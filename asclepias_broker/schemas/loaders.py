"""Marshmallow loaders."""

import idutils
from marshmallow import pre_load, Schema, fields, missing, post_load, validates_schema
from marshmallow.exceptions import ValidationError
from marshmallow.validate import OneOf

from ..datastore import Identifier, Relationship, Relation

DATACITE_RELATION_MAP = {
    'Cites': [
        ('Cites', False),
        ('IsCitedBy', True),
        ('References', False),
        ('IsReferencedBy', True),
    ],
    'IsSupplementTo': [
        ('IsSupplementTo', False),
        ('IsSupplementedBy', True),
    ],
    'HasVersion': [
        ('HasVersion', False),
        ('IsVersionOf', True),
        ('HasPart', False),
        ('IsPartOf', True),
    ],
    'IsIdenticalTo': [
        ('IsIdenticalTo', False),
    ]
}
INV_DATACITE_RELATION_MAP = dict(
    sum([[(vv, (k, inv)) for vv, inv in v]
         for k, v in DATACITE_RELATION_MAP.items()], []))


def from_scholix_relationship_type(rel_type):
    datacite_subtype = rel_type.get('SubType')
    if datacite_subtype and rel_type.get('SubTypeSchema') == 'DataCite':
        type_name = datacite_subtype
    else:
        type_name = rel_type['Name']
    rel_name, inversed = INV_DATACITE_RELATION_MAP.get(
        type_name, ('IsRelatedTo', False))
    return getattr(Relation, rel_name), inversed


class IdentifierSchema(Schema):

    @pre_load
    def remove_envelope(self, obj):
        return obj.get('Identifier', obj)

    value = fields.String(required=True, load_from='ID')
    scheme = fields.Function(
        deserialize=lambda s: s.lower(), required=True, load_from='IDScheme')

    @validates_schema
    def check_scheme(self, data):
        value = data['value']
        scheme = data['scheme'].lower()
        schemes = idutils.detect_identifier_schemes(value)
        if schemes and scheme not in schemes:
            raise ValidationError('Invalid scheme', 'IDScheme')

    @post_load
    def to_model(self, data):
        return Identifier(**data)


class RelationshipSchema(Schema):

    relation = fields.Method(
        deserialize='load_relation', load_from='RelationshipType')
    source = fields.Nested(IdentifierSchema, load_from='Source')
    target = fields.Nested(IdentifierSchema, load_from='Target')

    def load_relation(self, data):
        rel_name, self._inversed = from_scholix_relationship_type(data)
        return rel_name

    @post_load
    def to_model(self, data):
        if self._inversed:
            data['source'], data['target'] = data['target'], data['source']
        return Relationship(**data)


class EventSchema(Schema):

    EVENT_TYPES = {'relation_created', 'relation_deleted'}

    id = fields.UUID(required=True)
    event_type = fields.String(required=True, validate=OneOf(EVENT_TYPES))
    description = fields.String()
    creator = fields.String(required=True)
    source = fields.String(required=True)
    payload = fields.Nested(RelationshipSchema, many=True)
    time = fields.String(required=True, validate=str.isdigit)

    # TODO: Add event model...
    # @post_load
    # def to_model(self, data):
    #     # return Event(**data)
