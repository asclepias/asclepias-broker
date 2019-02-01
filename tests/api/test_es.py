# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 CERN.
#
# Asclepias Broker is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Test ElasticSearch indexing."""

from helpers import assert_es_equals_db, generate_payload, \
    reindex_all_relationships
from invenio_search import current_search

from asclepias_broker.events.api import EventAPI


def _group_data(id_):
    return {
        'Title': f'Title for {id_}',
        'Creator': [{'Name': f'Creator for {id_}'}],
        'Type': {'Name': 'literature'},
        'PublicationDate': '2018-01-01',
    }


def _rel_data():
    return {'LinkProvider': {'Name': 'Test provider'},
            'LinkPublicationDate': '2018-01-01'}


def _rel_with_metadata(src_id, relation, trg_id):
    return (
        src_id, relation, trg_id,
        {
            'Source': _group_data(src_id),
            'Target': _group_data(trg_id),
            **_rel_data(),
        }
    )


def _run_events_and_compare(events):
    current_search.flush_and_refresh('relationships')
    for ev in events:
        event = generate_payload(ev)
        EventAPI.handle_event(event)
        reindex_all_relationships()
        assert_es_equals_db()


def test_simple_groups(db, es_clear):
    """Test simple grouping events."""
    events = [
        _rel_with_metadata('A', 'Cites', 'X'),
        _rel_with_metadata('B', 'Cites', 'X'),
        _rel_with_metadata('C', 'Cites', 'X'),
        _rel_with_metadata('A', 'IsIdenticalTo', 'B'),
        _rel_with_metadata('B', 'IsIdenticalTo', 'C'),
        _rel_with_metadata('X', 'IsIdenticalTo', 'Y'),
    ]
    _run_events_and_compare(events)
