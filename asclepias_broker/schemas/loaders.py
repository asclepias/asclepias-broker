"""Marshmallow loaders."""

import arrow
import idutils
from copy import deepcopy
from marshmallow import (Schema, fields, missing, post_load, pre_load,
                         validates_schema)
from marshmallow.exceptions import ValidationError
from marshmallow.validate import OneOf

from ..datastore import Event, EventType, Identifier, Relation, Relationship
from .utils import to_model
from typing import Tuple

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

# Inverse mapping:
# <DataCiteRelation>: (<BrokerDBRelation>, Inverted?>)
# E.g.:
# 'IsVersionOf': ('HasVersion', True),
# 'HasVersion': ('HasVersion', False),
INV_DATACITE_RELATION_MAP = dict(
    sum([[(vv, (k, inv)) for vv, inv in v]
         for k, v in DATACITE_RELATION_MAP.items()], []))


def from_datacite_relation(relation: str) -> Tuple[Relation, bool]:
    relation, inversed = INV_DATACITE_RELATION_MAP.get(
        relation, ('IsRelatedTo', False))
    return getattr(Relation, relation), inversed


def from_scholix_relationship_type(rel_obj: dict) -> Tuple[Relation, bool]:
    # TODO: Rename this function to "from_scholix_relation"
    datacite_subtype = rel_obj.get('SubType')
    if datacite_subtype and rel_obj.get('SubTypeSchema') == 'DataCite':
        relation = datacite_subtype
    else:
        relation = rel_obj['Name']
    return from_datacite_relation(relation)


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
        obj2 = deepcopy(obj)
        for k in ('Source', 'Target'):
            obj2[k] = obj[k]['Identifier']
        return obj2

    def load_relation(self, data):
        rel_name, self._inversed = from_scholix_relationship_type(data)
        return rel_name

    @post_load
    def inverse(self, data):
        if self._inversed:
            data['Source'], data['Target'] = data['Target'], data['Source']
        return data


@to_model(Event)
class EventSchema(Schema):

    EVENT_TYPE_MAP = {
        'RelationshipCreated': EventType.RelationshipCreated,
        'RelationshipDeleted': EventType.RelationshipDeleted,
    }

    id = fields.UUID(required=True, load_from='ID')
    event_type = fields.Method(
        deserialize='get_event_type', required=True, validate=OneOf(EventType),
        load_from='EventType')
    description = fields.Str(load_from='Description')
    creator = fields.Str(required=True, load_from='Creator')
    source = fields.Str(required=True, load_from='Source')
    payload = fields.Method(deserialize='get_payload', required=True,
        load_from='Payload')
    time = fields.Method(deserialize='get_time', required=True,
        load_from='Time')

    @pre_load
    def store_original_payload(self, data):
        self.context['original_payload'] = data

    def get_event_type(self, obj):
        return self.EVENT_TYPE_MAP.get(obj, missing)

    def get_time(self, obj):
        return arrow.get(obj).datetime

    def get_payload(self, obj):
        return self.context['original_payload']
