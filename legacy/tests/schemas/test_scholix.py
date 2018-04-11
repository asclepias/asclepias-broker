"""Test Scholix marshmallow schema."""

import pytest

from asclepias_broker.models import Identifier, Relation, Relationship
from asclepias_broker.schemas.scholix import SCHOLIX_RELATIONS, \
    RelationshipSchema
from asclepias_broker.tasks import update_metadata
# from ..helpers import create_objects_from_relations


def id_dict(identifier, scheme=None):
    return {'ID': identifier, 'IDScheme': scheme or 'doi'}


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
        ([('A', Relation.IsSupplementTo, 'B')],
         {'Source': {'Title': 'TitleA'},
          'Target': {'Title': 'TitleB'},
          'LinkPublicationDate': '2018-01-01',
          'LinkProvider': [{'Name': 'Foobar'}]}),
        ('A', 'IsSupplementTo', 'B'),
        {},
    ),
])
def off_test_relationship_schema(broker, input_rel, output_rel, output_error):
    s = broker.session
    rels, payload = input_rel
    create_objects_from_relations(s, rels)
    relationship_obj = s.query(Relationship).one()
    update_metadata(s, relationship_obj, payload)
    relationship, errors = RelationshipSchema().dump(relationship_obj)
    if output_error:
        assert errors == output_error
    else:
        assert relationship == rel_dict(*output_rel)
