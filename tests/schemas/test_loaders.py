# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 CERN.
#
# Asclepias Broker is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Test marshmallow loaders."""

import arrow
from datetime import datetime
import pytest

from asclepias_broker.models import (Event, EventType, Identifier, Relation,
                                        Relationship)
from asclepias_broker.schemas.loaders import (EventSchema, IdentifierSchema,
                                              RelationshipSchema)
from asclepias_broker.schemas.scholix import SCHOLIX_RELATIONS


def compare_identifiers(a, b):
    assert a.value == b.value
    assert a.scheme == b.scheme


def compare_relationships(a, b):
    assert a.relation == b.relation
    compare_identifiers(a.source, b.source)
    compare_identifiers(a.target, b.target)


def compare_events(a, b):
    assert a.event_type == b.event_type
    assert a.description == b.description
    assert a.creator == b.creator
    assert a.source == b.source
    assert a.payload == b.payload
    assert a.time == b.time


def id_dict(identifier, scheme):
    return {'ID': identifier, 'IDScheme': scheme}


def id_obj(identifier, scheme):
    return Identifier(value=identifier, scheme=scheme)


def relation_dict(type_):
    if type_ not in SCHOLIX_RELATIONS:
        return {'Name': 'IsRelatedTo', 'SubType': type_,
                'SubTypeSchema': 'DataCite'}
    return {'Name': type_}


def rel_dict(source, relation, target):
    return {
        'Source': {'Identifier': id_dict(*source)},
        'RelationshipType': relation_dict(relation),
        'Target': {'Identifier': id_dict(*target)},
    }


def rel_obj(source, relation, target):
    return Relationship(source=id_obj(*source),
                        target=id_obj(*target),
                        relation=relation)


def ev_dict(type_, time, payload):
    return {
        'ID': '00000000-0000-0000-0000-000000000000',
        'EventType': type_,
        'Payload': payload,
        'Creator': 'Test creator',
        'Source': 'Test source',
        'Time': time,
    }


def ev_obj(type_, time, payload):
    return Event(
        id='00000000-0000-0000-0000-000000000000',
        event_type=type_,
        creator='Test creator',
        source='Test source',
        time=arrow.get(datetime(*time)),
        payload=payload,
    )


@pytest.mark.parametrize(('in_id', 'out_id', 'out_error'), [
    (('10.1234/1', 'DOI'), ('10.1234/1', 'doi'), {}),
    (('10.1234/1', 'foo'), None, {'IDScheme': ['Invalid scheme']}),
    (('http://id.com/123', 'URL'), ('http://id.com/123', 'url'), {}),
])
def test_identifier_schema(in_id, out_id, out_error):
    identifier, errors = IdentifierSchema().load(id_dict(*in_id))
    if out_error:
        assert errors == out_error
    else:
        assert not errors
        compare_identifiers(identifier, id_obj(*out_id))


@pytest.mark.parametrize(('in_rel', 'out_rel', 'out_error'), [
    (
        (('10.1234/A', 'DOI'), 'Cites', ('10.1234/B', 'DOI')),
        (('10.1234/A', 'doi'), Relation.Cites, ('10.1234/B', 'doi')),
        {},
    ),
    (
        (('10.1234/A', 'invalid_scheme'), 'Cites', ('10.1234/B', 'DOI')),
        None,
        {'Source': {'IDScheme': ['Invalid scheme']}},
    ),
])
def test_relationship_schema(in_rel, out_rel, out_error):
    relationship, errors = RelationshipSchema().load(rel_dict(*in_rel))
    if out_error:
        assert errors == out_error
    else:
        assert not errors
        compare_relationships(relationship, rel_obj(*out_rel))


@pytest.mark.parametrize(('in_ev', 'out_ev', 'out_error'), [
    (
        ('RelationshipCreated', '1517270400', {'test': 'payload'}),
        (EventType.RelationshipCreated, (2018, 1, 30)),
        {},
    ),
    (
        ('RelationshipDeleted', '1517270400', {'test': 'payload'}),
        (EventType.RelationshipDeleted, (2018, 1, 30)),
        {},
    ),
    (
        ('invalid_event_type', '1517270400', {'test': 'payload'}),
        None,
        {'EventType': ['Not a valid choice.']},
    ),
])
def test_event_schema(in_ev, out_ev, out_error):
    ev_payload = ev_dict(*in_ev)
    event, errors = EventSchema().load(ev_payload)
    if out_error:
        assert errors == out_error
    else:
        assert not errors
        compare_events(event, ev_obj(*out_ev, ev_payload))
