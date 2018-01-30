"""Marshmallow loaders."""

import arrow
import idutils
from marshmallow import (Schema, fields, missing, post_load, pre_load,
                         validates_schema)
from marshmallow.exceptions import ValidationError
from marshmallow.validate import OneOf

from ..datastore import Event, EventType, Identifier, Relation, Relationship
from .utils import to_model

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


@to_model(Identifier)
class IdentifierSchema(Schema):

    value = fields.Str(required=True, load_from='ID')
    scheme = fields.Function(
        deserialize=lambda s: s.lower(), required=True, load_from='IDScheme')

    @validates_schema
    def check_scheme(self, data):
        value = data['value']
        scheme = data['scheme'].lower()
        schemes = idutils.detect_identifier_schemes(value)
        if schemes and scheme not in schemes:
            raise ValidationError('Invalid scheme', 'IDScheme')


@to_model(Relationship)
class RelationshipSchema(Schema):

    relation = fields.Method(
        deserialize='load_relation', load_from='RelationshipType')
    source = fields.Nested(IdentifierSchema, load_from='Source')
    target = fields.Nested(IdentifierSchema, load_from='Target')

    @pre_load
    def remove_object_envelope(self, obj):
        for k in ('Source', 'Target'):
            obj[k] = obj[k]['Identifier']
        return obj

    def load_relation(self, data):
        rel_name, self._inversed = from_scholix_relationship_type(data)
        return rel_name

    @post_load
    def inverse(self, data):
        if self._inversed:
            data['source'], data['target'] = data['target'], data['source']
        return data


@to_model(Event)
class EventSchema(Schema):

    EVENT_TYPE_MAP = {
        'relationship_created': EventType.RelationshipCreated,
        'relationship_deleted': EventType.RelationshipDeleted,
    }

    id = fields.UUID(required=True)
    event_type = fields.Method(
        deserialize='get_event_type', required=True, validate=OneOf(EventType))
    description = fields.Str()
    creator = fields.Str(required=True)
    source = fields.Str(required=True)
    payload = fields.Method(deserialize='get_payload', required=True)
    time = fields.Method(deserialize='get_time', required=True)

    @pre_load
    def store_original_payload(self, data):
        self.context['original_payload'] = data

    def get_event_type(self, obj):
        return self.EVENT_TYPE_MAP.get(obj, missing)

    def get_time(self, obj):
        return arrow.get(obj).datetime

    def get_payload(self, obj):
        return self.context['original_payload']
