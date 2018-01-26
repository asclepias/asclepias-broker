"""Test marshmallow loaders."""

import pytest

from asclepias_broker.datastore import Identifier, Relation, Relationship
from asclepias_broker.schemas.loaders import (IdentifierSchema,
                                              RelationshipSchema)
from asclepias_broker.schemas.scholix import SCHOLIX_RELATIONS


def compare_identifiers(a, b):
    assert a.value == b.value
    assert a.scheme == b.scheme


def compare_relationships(a, b):
    assert a.relation == b.relation
    compare_identifiers(a.source, b.source)
    compare_identifiers(a.target, b.target)


def id_dict(identifier, scheme):
    return {'ID': identifier, 'IDScheme': scheme}


def id_obj(identifier, scheme):
    return Identifier(value=identifier, scheme=scheme)


def rel_type_dict(type_):
    if type_ not in SCHOLIX_RELATIONS:
        return {'Name': 'IsRelatedTo', 'SubType': type_,
                'SubTypeSchema': 'DataCite'}
    return {'Name': type_}


def rel_dict(source, rel_type, target):
    return {
        'Source': {'Identifier': id_dict(*source)},
        'RelationshipType': rel_type_dict(rel_type),
        'Target': {'Identifier': id_dict(*target)},
    }


def rel_obj(source, relation, target):
    return Relationship(source=id_obj(*source),
                        target=id_obj(*target),
                        relation=relation)


@pytest.mark.parametrize(('input_id', 'output_id', 'output_error'), [
    (('10.1234/1', 'DOI'), ('10.1234/1', 'doi'), {}),
    (('10.1234/1', 'foo'), None, {'IDScheme': ['Invalid scheme']}),
    (('http://id.com/123', 'URL'), ('http://id.com/123', 'url'), {}),
])
def test_identifier_schema(input_id, output_id, output_error):
    identifier, errors = IdentifierSchema().load(id_dict(*input_id))
    if output_error:
        assert errors == output_error
    else:
        compare_identifiers(identifier, id_obj(*output_id))


@pytest.mark.parametrize(('input_rel', 'output_rel', 'output_error'), [
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
def test_relationship_schema(input_rel, output_rel, output_error):
    relationship, errors = RelationshipSchema().load(rel_dict(*input_rel))
    if output_error:
        assert errors == output_error
    else:
        compare_relationships(relationship, rel_obj(*output_rel))
