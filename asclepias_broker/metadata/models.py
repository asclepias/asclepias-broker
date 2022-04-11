# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 CERN.
#
# Asclepias Broker is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
"""Metadata database models."""

from copy import deepcopy

import jsonschema
from invenio_db import db
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import backref
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy_utils.models import Timestamp
from sqlalchemy_utils.types import JSONType, UUIDType

from ..graph.models import Group, GroupRelationship
from ..jsonschemas import SCHOLIX_SCHEMA

COMMON_SCHEMA_DEFINITIONS = SCHOLIX_SCHEMA['definitions']
OBJECT_TYPE_SCHEMA = COMMON_SCHEMA_DEFINITIONS['ObjectType']
OVERRIDABLE_KEYS = {'Type', 'Title', 'Creator', 'PublicationDate'}
MERGEABLE_KEYS = {'Publisher', 'Keywords'}


class GroupMetadata(db.Model, Timestamp):
    """Metadata for a group."""

    __tablename__ = 'groupmetadata'

    # TODO: assert group.type == GroupType.Identity
    group_id = db.Column(
        UUIDType,
        db.ForeignKey(Group.id, onupdate='CASCADE', ondelete='CASCADE'),
        primary_key=True)
    group = db.relationship(
        Group,
        backref=backref('data', uselist=False),
        single_parent=True,
    )
    json = db.Column(
        db.JSON()
        .with_variant(postgresql.JSONB(none_as_null=True), 'postgresql')
        .with_variant(JSONType(), 'sqlite'),
        default=dict,
    )

    # Identifier metadata
    SCHEMA = {
        '$schema': 'http://json-schema.org/draft-06/schema#',
        'definitions': COMMON_SCHEMA_DEFINITIONS,
        'additionalProperties': False,
        'properties': {
            k: v for k, v in OBJECT_TYPE_SCHEMA['properties'].items()
            if k in OVERRIDABLE_KEYS or k in MERGEABLE_KEYS
        },
    }

    def update(self, payload: dict, validate: bool = True):
        """Update the metadata of a group."""
        new_json = deepcopy(self.json or {})
        for key in OVERRIDABLE_KEYS:
            if payload.get(key):
                if key == 'Type':
                    type_val = (payload['Type'] or {}).get('Name', 'unknown')
                    if type_val == 'unknown':
                        continue
                new_json[key] = payload[key]
        for key in MERGEABLE_KEYS:
            mergeKey(new_json, payload, key)
        # Set "Type" to "unknown" if not provided
        if not new_json.get('Type', {}).get('Name'):
            new_json['Type'] = {'Name': 'unknown'}
        if validate:
            jsonschema.validate(new_json, self.SCHEMA)
        self.json = new_json
        flag_modified(self, 'json')
        return self

def mergeKey(new_json: dict, payload: dict, key: str):
    
    if payload.get(key):
        if  not key in new_json.keys():
            new_json[key] = []
        for item in payload.get(key):
            #Should only be one item per dictionary here
            val = list(item.values())[0]
            current_values = [list(s.values())[0].lower() for s in new_json[key]]
            if val.lower() not in current_values:
                item_key = list(item.keys())[0]
                new_json[key].append({item_key : val})

class GroupRelationshipMetadata(db.Model, Timestamp):
    """Metadata for a group relationship."""

    __tablename__ = 'grouprelationshipmetadata'

    # TODO: assert group_relationship.type == GroupType.Identity
    group_relationship_id = db.Column(
        UUIDType,
        db.ForeignKey(
            GroupRelationship.id, onupdate='CASCADE', ondelete='CASCADE'),
        primary_key=True
    )
    group_relationship = db.relationship(
        GroupRelationship,
        backref=backref('data', uselist=False),
        single_parent=True,
    )
    json = db.Column(
        db.JSON()
        .with_variant(postgresql.JSONB(none_as_null=True), 'postgresql')
        .with_variant(JSONType(), 'sqlite'),
        default=list,
    )

    # Relationship metadata
    SCHEMA = {
        '$schema': 'http://json-schema.org/draft-06/schema#',
        'definitions': COMMON_SCHEMA_DEFINITIONS,
        'type': 'array',
        'items': {
            'type': 'object',
            'additionalProperties': False,
            'properties': {
                'LinkPublicationDate': {'$ref': '#/definitions/DateType'},
                'LinkProvider': {
                    'type': 'array',
                    'items': {'$ref': '#/definitions/PersonOrOrgType'}
                },
                'LicenseURL': {'type': 'string'},
            },
            'required': ['LinkPublicationDate', 'LinkProvider'],
        }
    }

    def update(self, payload: dict, validate: bool = True,
               multi: bool = False):
        """Updates the metadata of a group relationship."""
        new_json = deepcopy(self.json or [])
        if multi:
            new_json.extend(payload)
        else:
            new_json.append(payload)
        if validate:
            jsonschema.validate(new_json, self.SCHEMA)
        self.json = new_json
        flag_modified(self, 'json')
        return self
