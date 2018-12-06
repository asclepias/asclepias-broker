# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 CERN.
#
# Asclepias Harvester is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Harvester configuration."""

from kombu import Exchange

from .metadata import ADSMetadataHarvester, DOIMetadataHarvester

ASCLEPIAS_HARVESTER_HISTORY_PREFIX = 'asclepias-harvester'

ASCLEPIAS_HARVESTER_EVENT_HARVESTERS = {}
"""Event harvesters configuration.

Example for harvesting citations to Zenodo DOIs:

.. code-block:: python

    ASCLEPIAS_HARVESTER_EVENT_HARVESTERS = {
        'crossref': (CrossrefHarvester, {
            'id': 'zenodo-doi-references',
            'params': {
                'obj-id.prefix': '10.5281',
                'source': 'crossref',
                'relation-type': 'references',
            }
        }),
    }
"""

ASCLEPIAS_HARVESTER_METADATA_HARVESTERS = {
    'doi': (DOIMetadataHarvester, {}),
    'ads': (ADSMetadataHarvester, {}),
}

ASCLEPIAS_HARVESTER_ADS_API_TOKEN = None

ASCLEPIAS_HARVESTER_MQ_EXCHANGE = Exchange('harvester')

ASCLEPIAS_HARVESTER_METADATA_QUEUE = 'metadata-harvester'

ASCLEPIAS_HARVESTER_HARVEST_AFTER_EVENT_PROCESS = True
