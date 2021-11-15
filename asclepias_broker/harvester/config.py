# -*- coding: utf-8 -*-
#
# Copyright (C) 2018, 2019 CERN.
#
# Asclepias Harvester is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Harvester configuration."""

from kombu import Exchange

from .metadata import ADSMetadataHarvester, DOIMetadataHarvester
from .zenodo import ZenodoVersioningHarvester
from .github import GitHubHarvester
from .crossref import CrossrefHarvester
from .europepmc import EuropePMCHarvester

ASCLEPIAS_HARVESTER_HISTORY_PREFIX = 'asclepias-harvester'

ASCLEPIAS_HARVESTER_EVENT_HARVESTERS = {}
"""Event harvesters configuration.

Example for harvesting citations to Zenodo DOIs using the Crossref
and Europe PMC harvesters:

.. code-block:: python

"""
ASCLEPIAS_HARVESTER_EVENT_HARVESTERS = {
    'crossref': (CrossrefHarvester, {
        'id': 'zenodo-doi-references',
        'params': {
            'obj-id.prefix': '10.5281',
            'source': 'crossref',
            'relation-type': 'references',
        }
    }),
    'europepmc': (EuropePMCHarvester, {
        'id': 'zenodo-dois-query',
        'query': 'zenodo',
        'doi_prefix': '10.5281',
    }),
}

ASCLEPIAS_HARVESTER_METADATA_HARVESTERS = {
    'doi': (DOIMetadataHarvester, {}),
    'ads': (ADSMetadataHarvester, {}),
    'zenodo': (ZenodoVersioningHarvester, {}),
    'github': (GitHubHarvester, {})
}
"""Metadata harvesters configuration."""

ASCLEPIAS_HARVESTER_ADS_API_TOKEN = 'IkTy5gifaaE10RYXo7EfYsTU7lYg8zTTMZmrdcF8'
"""API token to be used when accessing the ADS REST API."""

ASCLEPIAS_HARVESTER_CROSSREF_API_EMAIL = None
"""Email address to be passed when accessing the Crossref REST API."""

ASCLEPIAS_HARVESTER_EUROPE_PMC_API_EMAIL = None
"""Email address to be passed when accessing the Europe PMC REST API."""

ASCLEPIAS_HARVESTER_MQ_EXCHANGE = Exchange('harvester')
"""RabbitMQ exchange for the harvester."""

ASCLEPIAS_HARVESTER_METADATA_QUEUE = 'metadata-harvester'
"""RabbitMQ queue name for the metadata harvester."""

ASCLEPIAS_HARVESTER_HARVEST_AFTER_EVENT_PROCESS = True
"""Controls post-event-process metadata harvesting for identifiers."""
