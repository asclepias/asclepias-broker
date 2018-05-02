# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 CERN.
#
# Asclepias Broker is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Test marshmallow loaders."""

from datetime import datetime

import arrow
import pytest
from helpers import gen_identifier, gen_relation

from asclepias_broker.models import Event, Identifier, Relation, \
    Relationship
from asclepias_broker.schemas.loaders import IdentifierSchema, \
    RelationshipSchema
from asclepias_broker.schemas.scholix import SCHOLIX_RELATIONS


def compare_identifiers(a, b):
    """Identifier comparator."""
    assert a.value == b.value
    assert a.scheme == b.scheme


def compare_relationships(a, b):
    """Relationship comparator."""
    assert a.relation == b.relation
    compare_identifiers(a.source, b.source)
    compare_identifiers(a.target, b.target)


def id_obj(identifier, scheme):
    """Identifier DB object generator."""
    return Identifier(value=identifier, scheme=scheme)


def rel_dict(source, relation, target):
    """Relationship dictionary generator."""
    return {
        'Source': {'Identifier': gen_identifier(*source)},
        'RelationshipType': gen_relation(relation),
        'Target': {'Identifier': gen_identifier(*target)},
    }


def rel_obj(source, relation, target):
    """Relationship DB object generator."""
    return Relationship(source=id_obj(*source),
                        target=id_obj(*target),
                        relation=relation)


@pytest.mark.parametrize(('in_id', 'out_id', 'out_error'), [
    (('10.1234/1', 'DOI'), ('10.1234/1', 'doi'), {}),
    (('10.1234/1', 'foo'), None, {'IDScheme': ["Invalid scheme 'foo'"]}),
    (('http://id.com/123', 'URL'), ('http://id.com/123', 'url'), {}),
])
def test_identifier_schema(in_id, out_id, out_error, db, es_clear):
    """Test the schema for identifier."""
    identifier, errors = IdentifierSchema().load(gen_identifier(*in_id))
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
        {'Source': {'IDScheme': ["Invalid scheme 'invalid_scheme'"]}},
    ),
])
def test_relationship_schema(in_rel, out_rel, out_error, db, es_clear):
    """Test the schema for relationship."""
    relationship, errors = RelationshipSchema().load(rel_dict(*in_rel))
    if out_error:
        assert errors == out_error
    else:
        assert not errors
        compare_relationships(relationship, rel_obj(*out_rel))
