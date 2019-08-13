# -*- coding: utf-8 -*-
#
# Copyright (C) 2019 CERN.
#
# Asclepias Broker is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Utilities for the Asclepias broker search module."""

import json
import time
from pathlib import Path

from invenio_search import current_search
from invenio_search import current_search_client as es_client

# NOTE: when prefixing is introduced from invenio-search v1.2.x, use this to
# build index/alias name:
#
#   from invenio_search.utils import build_alias_name


def get_write_index():
    """Get the current relationships write index.

    Since we're doing timestamp-based suffixing, the most recently created
    index is the one we use for writing.
    """
    return sorted(es_client.indices.get('relationships-*'))[-1]


def get_read_index():
    """Get the current relationships read index.

    Returns the index that is currently set to the "relationships" alias.
    """
    aliased_indices = es_client.indices.get_alias('relationships')
    assert len(aliased_indices) == 1
    return list(aliased_indices)[0]


def create_index():
    """Create a new relationships index with a timestamp suffix."""
    # Get the mapping
    mapping_path = current_search.mappings['relationships-v1.0.0']

    # Create a timestamp-suffixed index
    ts = str(time.time())
    index_name = f'relationships-v1.0.0-{ts}'
    es_client.indices.create(
        index=index_name,
        body=json.loads(Path(mapping_path).read_text()),
    )
    return index_name


def rollover_indices(keep_old_indices=1):
    """Sets the current write index to be the read index.

    Deletes the old read index by default.
    """
    old_index = get_read_index()
    new_index = get_write_index()
    assert old_index != new_index
    es_client.indices.update_aliases({'actions': [
        {'remove': {'index': old_index, 'alias': 'relationships'}},
        {'add': {'index': new_index, 'alias': 'relationships'}},
    ]})

    all_indices = sorted(es_client.indices.get('relationships-*'))
    indices_to_delete = all_indices[:-(1 + keep_old_indices)]
    for index in indices_to_delete:
        # make sure that the index is not currently aliased for reading
        assert index not in es_client.indices.get_alias('relationships')
        es_client.indices.delete(index=index)
