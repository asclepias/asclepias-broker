# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 CERN.
#
# Asclepias Harvester is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""DOI metadata harvester."""

from copy import deepcopy
from datetime import datetime
from typing import Callable, List, Union

import idutils
import requests
from flask import current_app
from werkzeug.utils import cached_property

from ..metadata.api import update_metadata
from .base import MetadataHarvester
from .crossref import CrossrefAPIException


class DataCiteAPIException(Exception):
    """DataCite REST API exception."""


class AdsAPIException(Exception):
    """Ads REST API exception."""


class MetadataAPIException(Exception):
    """Metadata REST API exception."""


def _date_from_parts(parts):
    """."""
    parts = list(reversed(parts))
    year = parts.pop()
    month = parts.pop() if parts else 1
    day = parts.pop() if parts else 1
    return f'{year}-{month:02d}-{day:02d}'


def crossref_metadata(doi: str) -> dict:
    """."""
    # TODO: Add "mailto" parameter as described in
    # https://www.eventdata.crossref.org/guide/service/query-api
    resp = requests.get(f'https://api.crossref.org/works/{doi}')
    if resp.ok:
        metadata = resp.json()['message']
        result = {}
        result['Identifier'] = [{'IDScheme': 'doi', 'ID': doi}]
        res_type = metadata['type']
        result['Type'] = {
            'Name': res_type if res_type == 'dataset' else 'literature',
        }
        if metadata.get('title'):
            result['Title'] = metadata['title'][0]
        creators = []
        for author_field in ('author', 'editor'):
            authors = metadata.get(author_field, [])
            for author in authors:
                if author.get('family') and author.get('given'):
                    creators.append(
                        '{}, {}'.format(author['family'], author['given']))
        if creators:
            result['Creator'] = [{'Name': c} for c in creators]

        if metadata.get('publisher'):
            result['Publisher'] = [{'Name': metadata['publisher']}]

        for date_field in ('issued', 'published-online', 'published-print'):
            if metadata.get(date_field):
                result['PublicationDate'] = _date_from_parts(
                    metadata[date_field]['date-parts'][0])
                break
        return result
    else:
        raise CrossrefAPIException()


def datacite_metadata(doi: str) -> dict:
    """."""
    # TODO: Consider using marshmallow for parsing these responses...
    mimetype = 'application/vnd.datacite.datacite+json'
    resp = requests.get(f'https://data.datacite.org/{mimetype}/{doi}')
    if resp.ok:
        metadata = resp.json()
        result = {}

        result['Identifier'] = [{'IDScheme': 'doi', 'ID': doi}]
        alt_ids = metadata.get('alternate_identifier') or []
        if not isinstance(alt_ids, list):
            alt_ids = [alt_ids]
        for ai in alt_ids:
            result['Identifier'].append({'IDScheme': ai['type'],
                                         'ID': ai['name']})

        res_type = metadata.get(
            'types', {}).get('resourceTypeGeneral', '').lower()
        result['Type'] = {
            'Name': (res_type if res_type in ('dataset', 'software')
                     else 'literature')
        }
        if metadata.get('title'):
            result['Title'] = metadata['title']

        creators = []
        if metadata.get('creator'):
            for author in metadata['creator']:
                if isinstance(author, str):
                    creators.append(author)
                elif author.get('name'):
                    creators.append(author['name'])
                elif author.get('familyName') and author.get('givenName'):
                    creators.append(
                        '{}, {}'.format(author['familyName'],
                                        author['givenName']))
        if creators:
            result['Creator'] = [{'Name': c} for c in creators]

        result['PublicationDate'] = metadata['date_published']
        return result
    else:
        raise DataCiteAPIException()


class DOIMetadataHarvester(MetadataHarvester):
    """Metadata harvester for DOIs."""

    DOI_ORG_AGENCY_API_URL = 'https://doi.org/doiRA'

    def __init__(self, *, doi_api_url: str = None, resolvers: dict = None,
                 provider_name: str = None):
        """."""
        self.doi_api_url = doi_api_url or self.DOI_ORG_AGENCY_API_URL
        self.resolvers = resolvers or {
            'crossref': crossref_metadata,
            'datacite': datacite_metadata,
        }
        self.provider_name = provider_name or "DOI metadata Harvester"

    def can_harvest(self, identifier: str, scheme: str,
                    providers: List[str] = None) -> bool:
        """."""
        is_provider = False
        if providers:
            is_provider = self.provider_name in providers
        return scheme.lower() == 'doi' and not is_provider

    def harvest(self, identifier: str, scheme: str,
                providers: List[str] = None):
        """."""
        data = self.get_metadata(identifier)
        if data:
            providers = set(providers) if providers else set()
            providers.add(self.provider_name)
            update_metadata(
                identifier, scheme, data,
                providers=list(providers))

    def get_metadata(self, doi: str) -> dict:
        """."""
        agency = self.get_agency(doi)
        resolver = self.resolvers.get(agency)
        if resolver:
            return resolver(doi)

    def get_agency(self, doi: str) -> str:
        """."""
        normalized_doi = idutils.normalize_doi(doi)
        doi_prefix = normalized_doi.split('/', 1)[0]
        return self._agency_by_prefix(doi_prefix)

    def _agency_by_prefix(self, doi_prefix):
        """."""
        res = requests.get(f'{self.doi_api_url}/{doi_prefix}')
        if res.ok:
            return res.json()[0].get('RA').lower()
        else:
            raise MetadataAPIException()


class ADSMetadataHarvester(MetadataHarvester):
    """Metadata harvester for DOIs."""

    ADS_API_URL = 'https://api.adsabs.harvard.edu/v1/search/query'
    ADS_API_PARAMS = {
        'fl': 'title,author,doi,bibcode,identifier,doctype,pub,year,pubdate',
    }

    ADS_TYPE_MAPPING = {
        'abstract': 'literature',
        'article': 'literature',
        'book': 'literature',
        'bookreview': 'literature',
        'catalog': 'literature',
        'circular': 'literature',
        'eprint': 'literature',
        'erratum': 'literature',
        'inbook': 'literature',
        'inproceedings': 'literature',
        'mastersthesis': 'literature',
        'misc': 'unknown',
        'newsletter': 'literature',
        'obituary': 'literature',
        'phdthesis': 'literature',
        'pressrelease': 'literature',
        'proceedings': 'literature',
        'proposal': 'literature',
        'software': 'software',
        'talk': 'literature',
        'techreport': 'literature',
    }

    def __init__(self, *, api_url: str = None, api_params: dict = None,
                 api_token: Union[str, Callable] = None,
                 provider_name: str = None):
        """."""
        self.api_url = api_url or self.ADS_API_URL
        self.api_params = api_params or self.ADS_API_PARAMS
        self._api_token = api_token
        self.provider_name = provider_name or "ADS metadata Harvester"

    def can_harvest(self, identifier: str, scheme: str,
                    providers: List[str] = None) -> bool:
        """."""
        is_provider = False
        if providers:
            is_provider = self.provider_name in providers

        return scheme.lower() == 'ads' and not is_provider

    def harvest(self, identifier: str, scheme: str,
                providers: List[str] = None):
        """."""
        data = self.get_metadata(identifier)
        if data:
            providers = set(providers) if providers else set()
            providers.add(self.provider_name)
            update_metadata(
                identifier, scheme, data,
                providers=list(providers))

    def get_metadata(self, bibcode: str) -> dict:
        """."""
        params = deepcopy(self.api_params)
        params['q'] = f'identifier:{bibcode}'
        res = requests.get(
            self.api_url, params=params, headers=self._req_headers)
        if res.ok:
            data = res.json()
            if data['response']['numFound'] == 1:
                doc = data['response']['docs'][0]
                return {
                    'Identifier': self._extract_identifiers(doc),
                    'Publisher': ([{'Name': doc['pub']}]
                                  if doc.get('pub') else None),
                    'Creator': [{'Name': n} for n in doc.get('author', [])
                                if n],
                    'Title': doc.get('title', [None])[0],
                    'PublicationDate': self._extract_date(doc),
                    'Type': {'Name': self._extract_type(doc)},
                }
        else:
            raise AdsAPIException()

    @cached_property
    def api_token(self):
        """."""
        if self._api_token is None:
            self._api_token = current_app.config.get(
                'ASCLEPIAS_HARVESTER_ADS_API_TOKEN')
        elif callable(self._api_token):
            self._api_token = self._api_token()
        return self._api_token

    @cached_property
    def _req_headers(self):
        """."""
        return {'Authorization': f'Bearer:{self.api_token}'}

    def _extract_date(self, data):
        """."""
        try:
            return datetime.strptime(
                data.get('pubdate'), '%Y-%m-%d').isoformat()
        except Exception:
            return data.get('year')

    def _extract_identifiers(self, data):
        """."""
        ids = set()
        if data.get('bibcode'):
            ids.add((data.get('bibcode'), 'ads'))
        ids |= {(d, 'doi') for d in data.get('doi', []) if d}
        for id_ in data.get('identifier', []):
            try:
                ids.add((id_, idutils.detect_identifier_schemes(id_)[0]))
            except Exception:
                pass
        return [{'ID': i, 'IDScheme': s} for i, s in ids if i and s]

    def _extract_type(self, data):
        """."""
        return self.ADS_TYPE_MAPPING.get(data.get('doctype', 'unknown'))
