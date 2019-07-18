# -*- coding: utf-8 -*-
#
# Copyright (C) 2019 CERN.
#
# Asclepias Harvester is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""ArXiv metadata harvester."""

from typing import List

import arxiv

from .base import MetadataHarvester
from .metadata import update_metadata


class ArxivAPIException(Exception):
    """ArXiv REST API exception."""


class ArxivClient:
    """ArXiv client."""

    def get_metadata(self, arxiv_id):
        """Get metadata from ArXiv."""
        res = arxiv.query(query="",
                          id_list=[arxiv_id],
                          max_results=None,
                          start=0,
                          sort_by="relevance",
                          sort_order="descending",
                          prune=True,
                          iterative=False,
                          max_chunk_results=1000)

        if len(res) == 0:
            raise ArxivAPIException()
        else:
            return res[0]


class ArxivMetadataHarvester(MetadataHarvester):
    """Metadata harvester for ArXiv records' metadata."""

    def __init__(self, *, provider_name: str = None):
        """."""
        self.provider_name = provider_name or "ArXiv versioning harvester"

    def can_harvest(self, identifier: str, scheme: str,
                    providers: List[str] = None) -> bool:
        """."""
        is_provider = False
        if providers:
            is_provider = self.provider_name in providers

        return self._is_arxiv_doi(identifier) and not is_provider

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

    def _is_arxiv_doi(self, identifier: str) -> bool:
        if identifier.lower().startswith('arxiv:'):
            return True
        else:
            return False

    def get_metadata(self, arxiv_id):
        """."""
        client = ArxivClient()

        arxiv_id.replace('arXiv:', '')
        metadata = client.get_metadata(arxiv_id)
        result = {}

        # Identifiers
        result['Identifier'] = []
        doi = metadata['doi']
        if doi:
            result['Identifier'].append({'IDScheme': 'doi', 'ID': doi})

        # Type
        result['Type'] = {'Name': 'literature'}

        # Title
        result['Title'] = metadata['title']

        # Creators
        result['Creator'] = [{'Name': c} for c in metadata['authors']]

        # Publication date
        result['PublicationDate'] = metadata['published']

        return result
