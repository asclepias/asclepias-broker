# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 CERN.
#
# Asclepias Broker is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Test search endpoint."""

from flask import url_for
from helpers import generate_payload, reindex_all_relationships

from asclepias_broker.events.api import EventAPI


def test_invalid_search_parameters(client):
    search_url = url_for('invenio_records_rest.relid_list')

    params = {}
    resp = client.get(search_url)
    assert resp.status_code == 400
    assert resp.json['message'] == 'Validation error.'
    assert resp.json['errors'][0]['field'] == 'id'

    params['id'] = 'some-id'
    resp = client.get(search_url, query_string=params)
    assert resp.status_code == 400
    assert resp.json['message'] == 'Validation error.'
    assert len(resp.json['errors']) == 1
    assert resp.json['errors'][0]['field'] == 'scheme'

    params['scheme'] = 'doi'
    resp = client.get(search_url, query_string=params)
    assert resp.status_code == 400
    assert resp.json['message'] == 'Validation error.'
    assert len(resp.json['errors']) == 1
    assert resp.json['errors'][0]['field'] == 'relation'

    params['relation'] = 'not-a-valid-value'
    resp = client.get(search_url, query_string=params)
    assert resp.status_code == 400
    assert resp.json['message'] == 'Validation error.'
    assert len(resp.json['errors']) == 1
    assert resp.json['errors'][0]['field'] == 'relation'

    params['relation'] = 'isCitedBy'
    resp = client.get(search_url, query_string=params)
    assert resp.status_code == 200


def _normalize_results(results):
    normalized = set()
    for hit in results['hits']['hits']:
        rel = hit['metadata']
        src_ids = frozenset(i['ID'] for i in rel['Source']['Identifier'])
        trg_ids = frozenset(i['ID'] for i in rel['Target']['Identifier'])
        normalized.add((src_ids, rel['RelationshipType'], trg_ids))
    return normalized


def _process_events(events):
    for e in events:
        EventAPI.handle_event(generate_payload(e))
    reindex_all_relationships()


def test_simple_citations(client, db, es_clear):
    search_url = url_for('invenio_records_rest.relid_list')
    params = {'id': 'X', 'scheme': 'doi', 'relation': 'isCitedBy'}

    _process_events([
        ['A', 'Cites', 'X']
    ])

    resp = client.get(search_url, query_string=params)
    assert resp.status_code == 200
    assert resp.json['hits']['total'] == 1
    assert _normalize_results(resp.json) == {
        (frozenset('A'), 'Cites', frozenset('X')),
    }

    _process_events([
        [src, 'Cites', 'X']
        for src in ('B', 'C', 'D', 'E', 'F', 'G')
    ])

    citations_sources = ('A', 'B', 'C', 'D', 'E', 'F', 'G')
    resp = client.get(search_url, query_string=params)
    assert resp.status_code == 200
    assert resp.json['hits']['total'] == 7
    assert _normalize_results(resp.json) == {
        (frozenset(src), 'Cites', frozenset('X'))
        for src in citations_sources
    }

    for i in citations_sources:
        params['id'] = i
        resp = client.get(search_url, query_string=params)
        assert resp.status_code == 200
        assert resp.json['hits']['total'] == 0
