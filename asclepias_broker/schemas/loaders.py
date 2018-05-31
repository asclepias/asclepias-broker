# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 CERN.
#
# Asclepias Broker is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Marshmallow loaders."""

from copy import deepcopy
from typing import Tuple

import arrow
import idutils
from arrow.parser import ParserError
from marshmallow import Schema, fields, missing, post_load, pre_load, \
    validates, validates_schema
from marshmallow.exceptions import ValidationError
from marshmallow.validate import OneOf

from ..models import Event, Identifier, Relation, Relationship

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


def to_model(model_cls):
    """Marshmallow schema decorator for creating SQLAlchemy models."""
    def inner(Cls):
        class ToModelSchema(Cls):

            def __init__(self, *args, check_existing=False, **kwargs):
                kwargs.setdefault('context', {})
                kwargs['context'].setdefault('check_existing', check_existing)
                super().__init__(*args, **kwargs)

            @post_load
            def to_model(self, data):
                if self.context.get('check_existing'):
                    return model_cls.get(**data) or model_cls(**data)
                return model_cls(**data)
        return ToModelSchema
    return inner


def from_datacite_relation(relation: str) -> Tuple[Relation, bool]:
    """Get normalized relationship type value of a datacite relationship."""
    relation, inversed = INV_DATACITE_RELATION_MAP.get(
        relation, ('IsRelatedTo', False))
    return getattr(Relation, relation), inversed


def from_scholix_relation(rel_obj: dict) -> Tuple[Relation, bool]:
    """Get normalized rleationship type value from a Scholix relationship."""
    datacite_subtype = rel_obj.get('SubType')
    if datacite_subtype and rel_obj.get('SubTypeSchema') == 'DataCite':
        relation = datacite_subtype
    else:
        relation = rel_obj['Name']
    return from_datacite_relation(relation)


@to_model(Identifier)
class IdentifierSchema(Schema):
    """Identifier loader schema."""

    value = fields.Str(required=True, load_from='ID')
    scheme = fields.Function(
        deserialize=lambda s: s.lower(), required=True, load_from='IDScheme')

    @validates_schema
    def check_scheme(self, data):
        """Validate the provided identifier scheme."""
        value = data['value']
        scheme = data['scheme'].lower()
        schemes = idutils.detect_identifier_schemes(value)
        # TODO: "pmid" scheme with value '11781516' collides (with ean8)
        # if schemes and scheme not in schemes:
        #     raise ValidationError("Invalid scheme '{}'".format(
        #         data['scheme']), 'IDScheme')


@to_model(Relationship)
class RelationshipSchema(Schema):
    """Relationship loader schema."""

    relation = fields.Method(
        deserialize='load_relation', load_from='RelationshipType')
    source = fields.Nested(IdentifierSchema, load_from='Source')
    target = fields.Nested(IdentifierSchema, load_from='Target')

    @pre_load
    def remove_object_envelope(self, obj):
        """Remove the envelope for the Source and Target identifier fields."""
        obj2 = deepcopy(obj)
        for k in ('Source', 'Target'):
            obj2[k] = obj[k]['Identifier']
        return obj2

    def load_relation(self, data):
        """Load the relation type value."""
        rel_name, self._inversed = from_scholix_relation(data)
        return rel_name

    @post_load
    def inverse(self, data):
        """Normalize the relationship direction based on its type."""
        if data['source'].value == data['target'].value \
                and data['source'].scheme == data['target'].scheme:
            raise ValidationError("Invalid source '{}' and target '{}'".format(
                data['source'], data['target']),
                "Souce and target should not be equal.")

        if self._inversed:
            data['source'], data['target'] = data['target'], data['source']

        return data
