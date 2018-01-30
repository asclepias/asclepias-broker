"""Test Scholix marshmallow schema."""

import pytest

from asclepias_broker.datastore import Identifier, Relation, Relationship
from asclepias_broker.schemas.scholix import (SCHOLIX_RELATIONS,
                                              RelationshipSchema)


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


@pytest.mark.parametrize(('input_rel', 'output_rel', 'output_error'), [
    (
        (('10.1234/A', 'doi'), Relation.Cites, ('10.1234/B', 'doi')),
        (('10.1234/A', 'doi'), 'Cites', ('10.1234/B', 'doi')),
        {},
    ),
    (
        (('10.1234/A', 'doi'), Relation.IsSupplementTo, ('10.1234/B', 'doi')),
        (('10.1234/A', 'doi'), 'IsSupplementTo', ('10.1234/B', 'doi')),
        {},
    ),
])
def test_relationship_schema(input_rel, output_rel, output_error):
    relationship, errors = RelationshipSchema().dump(rel_obj(*input_rel))
    if output_error:
        assert errors == output_error
    else:
        assert relationship == rel_dict(*output_rel)
