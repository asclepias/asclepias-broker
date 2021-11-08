# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 CERN.
#
# Asclepias Harvester is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Versioning metadata harvester."""

from copy import deepcopy
from datetime import datetime
from typing import List

import requests
from flask import current_app

from ..utils import chunks
from .base import MetadataHarvester


class ZenodoAPIException(Exception):
    """Zenodo REST API exception."""


class ZenodoClient:
    """Zenodo client."""

    url = 'https://zenodo.org/api/records'
    params = {
        'page': 1,
        'size': 100,
        'all_versions': True,
        'sort': '-version'
    }

    def get_concept_doi(self, doi: str) -> str:
        """."""
        query = 'doi:"{}"'.format(doi)
        params = deepcopy(self.params)
        params['q'] = query

        res = requests.get(self.url, params=params)
        conceptdoi = None
        if res.ok:
            if res.json()['hits']['total'] == 1:
                conceptdoi = res.json()['hits']['hits'][0].get('conceptdoi')
            else:
                conceptdoi = doi  # it's already a conceptdoi
        else:
            try:
                res.raise_for_status()
            except Exception as exc:
                raise ZenodoAPIException(exc)
        return conceptdoi

    def get_versions(self, conceptdoi) -> List[str]:
        """."""
        query = 'conceptdoi:"{}"'.format(conceptdoi)
        params = deepcopy(self.params)
        params['q'] = query
        url = self.url
        while True:
            res = requests.get(url, params=params)
            if not res.ok:
                res.raise_for_status()

            data = res.json()
            for r in data['hits']['hits']:
                yield r['doi']
            if data['links'].get('next'):
                url = data['links'].get('next')
                params = {
                    'all_versions': True
                }
            else:
                break


class ZenodoVersioningHarvester(MetadataHarvester):
    """Metadata harvester for Zenodo records' versioning."""

    def __init__(self, *, provider_name: str = None):
        """."""
        self.provider_name = provider_name or "Zenodo versioning harvester"

    def can_harvest(self, identifier: str, scheme: str,
                    providers: List[str] = None) -> bool:
        """."""
        is_provider = False
        if providers:
            is_provider = self.provider_name in providers

        return self._is_zenodo_doi(scheme, identifier) and not is_provider

    def harvest(self, identifier: str, scheme: str,
                providers: List[str] = None):
        """."""
        try:
            conceptdoi, versions = self.get_versioning_metadata(identifier)
            if conceptdoi:
                providers = set(providers) if providers else set()
                providers.add(self.provider_name)
                update_versioning(conceptdoi, versions, 'doi',
                                providers=list(providers))
        except Exception as exc:
            raise ZenodoAPIException(exc)

    def _is_zenodo_doi(self,  scheme: str, identifier: str) -> bool:
        if scheme.lower() == 'doi' and identifier.lower()\
                .startswith('10.5281/zenodo.'):
            return True
        else:
            return False

    def get_versioning_metadata(self, doi: str):
        """."""
        client = ZenodoClient()
        conceptdoi = client.get_concept_doi(doi)
        versions = None
        if conceptdoi:
            versions = client.get_versions(conceptdoi)
        return conceptdoi, versions


def update_versioning(parent_identifier: str, child_identifiers: List[str],
                      scheme: str, providers: List[str] = None,
                      link_publication_date: str = None):
    """."""
    from ..events.api import EventAPI

    providers = providers or ['unknown']
    providers = [{'Name': provider} for provider in providers]
    link_publication_date = link_publication_date or \
        datetime.now().isoformat()
    source_identifier = {
                    "ID": parent_identifier,
                    "IDScheme": scheme
                }
    event = []

    for identifier in child_identifiers:
        target_identifier = {
                    "ID": identifier,
                    "IDScheme": scheme
                }
        payload = {
            'RelationshipType': {
                'Name': 'IsRelatedTo',
                'SubTypeSchema': 'DataCite',
                'SubType': 'HasVersion'
            },
            'Target': {
                'Identifier': target_identifier,
                'Type': {'Name': 'unknown'}
            },
            'LinkProvider': providers,
            'Source': {
                'Identifier': source_identifier,
                'Type': {'Name': 'unknown'}
            },
            'LinkPublicationDate': link_publication_date,
        }
        event.append(payload)

    for event_chunk in chunks(event, 100):
        try:
            EventAPI.handle_event(list(event_chunk), no_index=True, eager=True)
        except ValueError:
            current_app.logger.exception(
                'Error while processing versioning event.')
