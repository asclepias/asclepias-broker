# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 CERN.
#
# Asclepias Broker is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Test ElasticSearch indexing."""

from helpers import generate_payload
from invenio_search import current_search
from invenio_search.api import RecordsSearch

from asclepias_broker.api import EventAPI
from asclepias_broker.models import GroupRelationship, GroupType


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


def normalize_es_result(es_result):
    """Turn a single ES result (relationship doc) into a normalized format."""
    return (
        ('RelationshipType', es_result['RelationshipType']),
        ('Grouping', es_result['Grouping']),
        ('ID', es_result['ID']),
        ('SourceID', es_result['Source']['ID']),
        ('TargetID', es_result['Target']['ID']),
    )


def normalize_db_result(db_result):
    """Turn a single DB result (GroupRelationship) into a normalized format."""
    # For Identity GroupRelationships and for SourceID we fetch a
    # Version Group of the source
    if db_result.type == GroupType.Identity:
        source_id = db_result.source.supergroupsm2m[0].group.id
    else:
        source_id = db_result.source.id

    return (
        ('RelationshipType', db_result.relation.name),
        ('Grouping', db_result.type.name.lower()),
        ('ID', str(db_result.id)),
        ('SourceID', str(source_id)),
        ('TargetID', str(db_result.target.id)),
    )


def assert_es_equals_db():
    """Assert that the relationships in ES the GroupRelationships in DB.

    NOTE: This tests takes the state of the DB as the reference for comparison.
    """
    # Wait for ES to be available
    current_search.flush_and_refresh('relationships')

    # Fetch all DB objects and all ES objects
    es_q = list(RecordsSearch(index='relationships').query().scan())
    db_q = GroupRelationship.query.all()

    # normalize and compare two sets
    es_norm_q = list(map(normalize_es_result, es_q))
    db_norm_q = list(map(normalize_db_result, db_q))
    assert set(es_norm_q) == set(db_norm_q)


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
    current_search.flush_and_refresh('relationships')
    for evtsrc in events:
        event = generate_payload(evtsrc)
        EventAPI.handle_event(event)
        assert_es_equals_db()
