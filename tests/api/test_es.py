# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 CERN.
#
# Asclepias Broker is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Test ElasticSearch indexing."""

from helpers import assert_es_equals_db, generate_payload
from invenio_search import current_search

from asclepias_broker.api import EventAPI


def _group_data(id_):
    return {
        'Title': 'Title for {}'.format(id_),
        'Creator': [{'Name': 'Creator for {}'.format(id_)}],
        'Type': {'Name': 'literature'},
        'PublicationDate': '2018-01-01',
    }


def _rel_data():
    return {'LinkProvider': {'Name': 'Test provider'},
            'LinkPublicationDate': '2018-01-01'}


def _scholix_data(src_id, trg_id):
    return {
        'Source': _group_data(src_id),
        'Target': _group_data(trg_id),
        **_rel_data(),
    }


def run_events_and_compare(events):
    current_search.flush_and_refresh('relationships')
    for evtsrc in events:
        event = generate_payload(evtsrc)
        EventAPI.handle_event(event)
        assert_es_equals_db()


def test_simple_groups(db, es_clear):
    """Test simple grouping events."""
    events = [
        (['C', 'A', 'Cites', 'X', '2018-01-01'], _scholix_data('A', 'X')),
        (['C', 'B', 'Cites', 'X', '2018-01-01'], _scholix_data('B', 'X')),
        (['C', 'C', 'Cites', 'X', '2018-01-01'], _scholix_data('C', 'X')),
        (['C', 'D', 'Cites', 'Y', '2018-01-01'], _scholix_data('C', 'X')),
        (['C', 'A', 'IsIdenticalTo', 'B', '2018-01-01'],
         _scholix_data('A', 'B')),
        (['C', 'B', 'IsIdenticalTo', 'C', '2018-01-01'],
         _scholix_data('B', 'C')),
        (['C', 'X', 'IsIdenticalTo', 'Y', '2018-01-01'],
         _scholix_data('X', 'Y')),
    ]
    run_events_and_compare(events)
