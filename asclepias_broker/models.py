# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 CERN.
# Copyright (c) 2017 Thomas P. Robitaille.
#
# Asclepias Broker is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
"""Database models."""

import enum
import uuid
from copy import deepcopy

import jsonschema
from invenio_db import db
from sqlalchemy import JSON, Boolean, Column, Enum, ForeignKey, Integer, String
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import backref
from sqlalchemy.orm import relationship as orm_relationship
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy.schema import Index, PrimaryKeyConstraint, UniqueConstraint
from sqlalchemy.types import DateTime
from sqlalchemy_utils.models import Timestamp
from sqlalchemy_utils.types import JSONType, UUIDType

from .jsonschemas import SCHOLIX_SCHEMA


class Relation(enum.Enum):
    """Relation type."""

    Cites = 1
    IsSupplementTo = 2
    HasVersion = 3
    IsIdenticalTo = 4
    IsRelatedTo = 5


class EventType(enum.Enum):
    """Event type."""

    RelationshipCreated = 1
    RelationshipDeleted = 2


class PayloadType(enum.Enum):
    """Payload type."""

    Relationship = 1
    Identifier = 2


class GroupType(enum.Enum):
    """Group type."""

    Identity = 1
    Version = 2


class Identifier(db.Model, Timestamp):
    """Identifier model."""

    __tablename__ = 'identifier'
    __table_args__ = (
        UniqueConstraint('value', 'scheme',
                         name='uq_identifier_value_scheme'),
        Index('ix_identifier_value', 'value'),
        Index('ix_identifier_scheme', 'scheme'),
    )
    id = Column(UUIDType, default=uuid.uuid4, primary_key=True)
    value = Column(String)
    scheme = Column(String)

    def __repr__(self):
        """String representation of the Identifier."""
        return "<{self.scheme}: {self.value}>".format(self=self)

    @classmethod
    def get(cls, value=None, scheme=None, **kwargs):
        """Get the identifier from the database."""
        return cls.query.filter_by(
            value=value, scheme=scheme).one_or_none()

    def fetch_or_create_id(self):
        """Fetches from the database or creates an id for the identifier."""
        if not self.id:
            obj = self.get(self.value, self.scheme)
            if obj:
                self = obj
            else:
                self.id = uuid.uuid4()
        return self

    def _get_related(self, condition, relationship, with_deleted=False):
        cond = condition & (Relationship.relation == relationship)
        if not with_deleted:
            cond &= (Relationship.deleted.is_(False))
        return Relationship.query.filter(cond)

    def _get_identities(self, as_relation=False):
        """Get the first-layer of 'Identical' Identifies."""
        cond = ((Relationship.source == self) | (Relationship.target == self))
        q = self._get_related(cond, Relation.IsIdenticalTo)
        if as_relation:
            return q.all()
        else:
            siblings = set(sum([[item.source, item.target] for item in q], []))
            if siblings:
                return list(siblings)
            else:
                return [self, ]

    def get_identities(self):
        """Get the fully-expanded list of 'Identical' Identifiers."""
        ids = next_ids = set([self])
        while next_ids:
            grp = set(sum([item._get_identities() for item in next_ids], []))
            next_ids = grp - ids
            ids |= grp
        return list(ids)

    def get_parents(self, rel_type, as_relation=False):
        """Get all parents of given Identifier for given relation."""
        q = self._get_related((Relationship.target == self), rel_type)
        if as_relation:
            return q.all()
        else:
            return [item.source for item in q]

    def get_children(self, rel_type, as_relation=False):
        """Get all children of given Identifier for given relation."""
        q = self._get_related((Relationship.source == self), rel_type)
        if as_relation:
            return q.all()
        else:
            return [item.target for item in q]

    @property
    def identity_group(self):
        """Get the identity group the identifier belongs to."""
        return next((id2g.group for id2g in self.id2groups
                     if id2g.group.type == GroupType.Identity), None)

    @property
    def data(self):
        """Get the metadata of the identity group the identifier belongs to."""
        if self.identity_group and self.identity_group.data:
            return self.identity_group.data.json


class Relationship(db.Model, Timestamp):
    """Relationship between two identifiers."""

    __tablename__ = 'relationship'
    __table_args__ = (
        UniqueConstraint('source_id', 'target_id', 'relation',
                         name='uq_relationship_source_target_relation'),
        Index('ix_relationship_source', 'source_id'),
        Index('ix_relationship_target', 'target_id'),
        Index('ix_relationship_relation', 'relation'),
    )

    id = Column(UUIDType, default=uuid.uuid4, primary_key=True)
    source_id = Column(UUIDType,
                       ForeignKey(Identifier.id, onupdate='CASCADE',
                                  ondelete='CASCADE'),
                       nullable=False)
    target_id = Column(UUIDType, ForeignKey(Identifier.id, onupdate='CASCADE',
                                            ondelete='CASCADE'),
                       nullable=False)
    relation = Column(Enum(Relation))
    deleted = Column(Boolean, default=False)

    source = orm_relationship(Identifier, foreign_keys=[source_id],
                              backref='sources')
    target = orm_relationship(Identifier, foreign_keys=[target_id],
                              backref='targets')

    @classmethod
    def get(cls, source, target, relation, **kwargs):
        """Get the relationship from the database."""
        return cls.query.filter_by(
            source_id=source.id, target_id=target.id,
            relation=relation).one_or_none()

    def fetch_or_create_id(self):
        """Fetches from the database or creates an id for the relationship."""
        self.source = self.source.fetch_or_create_id()
        self.target = self.target.fetch_or_create_id()

        if not self.id:
            obj = self.get(self.source, self.target, self.relation)
            if obj:
                self = obj
            else:
                self.id = uuid.uuid4()
        return self

    @property
    def identity_group(self):
        """Get the relationship's identity group."""
        return GroupRelationship.query.filter_by(
            source=self.source.identity_group,
            target=self.target.identity_group,
            relation=self.relation,
            type=GroupType.Identity).one_or_none()

    @property
    def data(self):
        """Get the relationship's identity group metadata."""
        if self.identity_group and self.identity_group.data:
            return self.identity_group.data.json

    def __repr__(self):
        """String representation of the relationship."""
        return (
            '<{self.source.value} {self.relation.name} '
            '{self.target.value}{deleted}>'
            .format(self=self, deleted=" [D]" if self.deleted else "")
        )


class Event(db.Model, Timestamp):
    """Event model."""

    __tablename__ = 'event'

    id = Column(UUIDType, primary_key=True)
    description = Column(String, nullable=True)
    event_type = Column(Enum(EventType))
    creator = Column(String)
    source = Column(String)
    payload = Column(JSONType)
    time = Column(DateTime)

    @classmethod
    def get(cls, id=None, **kwargs):
        """Get the event from the database."""
        return cls.query.filter_by(id=id).one_or_none()

    def __repr__(self):
        """String representation of the event."""
        return "<{self.id}: {self.time}>".format(self=self)


class ObjectEvent(db.Model, Timestamp):
    """Event related to an Identifier or Relationship."""

    __tablename__ = 'objectevent'
    __table_args__ = (
        PrimaryKeyConstraint(
            'event_id', 'object_uuid', 'payload_type', 'payload_index',
            name='pk_objectevent'),
    )

    event_id = Column(UUIDType, ForeignKey(Event.id), nullable=False)
    object_uuid = Column(UUIDType, nullable=False)
    payload_type = Column(Enum(PayloadType), nullable=False)
    payload_index = Column(Integer, nullable=False)

    def __repr__(self):
        """String representation of the object event."""
        return "<{self.event_id}: {self.object_uuid}>".format(self=self)


class Group(db.Model, Timestamp):
    """Group model."""

    __tablename__ = 'group'

    id = Column(UUIDType, default=uuid.uuid4, primary_key=True)
    type = Column(Enum(GroupType), nullable=False)

    identifiers = orm_relationship(
        Identifier,
        secondary=lambda: Identifier2Group.__table__,
        backref='groups',
        viewonly=True)

    groups = orm_relationship(
        'Group',
        secondary=lambda: GroupM2M.__table__,
        primaryjoin=lambda: (Group.id == GroupM2M.group_id),
        secondaryjoin=lambda: (Group.id == GroupM2M.subgroup_id))

    def __repr__(self):
        """String representation of the group."""
        return "<{self.id}: {self.type.name}>".format(self=self)


class GroupRelationship(db.Model, Timestamp):
    """Group relationship model."""

    __tablename__ = 'grouprelationship'
    __table_args__ = (
        UniqueConstraint('source_id', 'target_id', 'relation',
                         name='uq_grouprelationship_source_target_relation'),
        Index('ix_grouprelationship_source', 'source_id'),
        Index('ix_grouprelationship_target', 'target_id'),
        Index('ix_grouprelationship_relation', 'relation'),
    )

    id = Column(UUIDType, default=uuid.uuid4, primary_key=True)
    type = Column(Enum(GroupType), nullable=False)
    relation = Column(Enum(Relation), nullable=False)
    source_id = Column(UUIDType, ForeignKey(Group.id, ondelete='CASCADE',
                                            onupdate='CASCADE'),
                       nullable=False)
    target_id = Column(UUIDType, ForeignKey(Group.id, ondelete='CASCADE',
                                            onupdate='CASCADE'),
                       nullable=False)

    # DB relationships
    source = orm_relationship(
        Group, foreign_keys=[source_id], backref='sources')
    target = orm_relationship(
        Group, foreign_keys=[target_id], backref='targets')

    relationships = orm_relationship(
        'GroupRelationship',
        secondary=lambda: GroupRelationshipM2M.__table__,
        primaryjoin=lambda: (GroupRelationship.id ==
                             GroupRelationshipM2M.relationship_id),
        secondaryjoin=lambda: (GroupRelationship.id ==
                               GroupRelationshipM2M.subrelationship_id))

    # TODO:
    # We don't store 'deleted' as in the relation as most likely don't need
    # that as 'ground truth' in precomputed groups anyway

    def __repr__(self):
        """String representation of the group relationship."""
        return ('<{self.source} {self.relation.name} {self.target}>'
                .format(self=self))


class Identifier2Group(db.Model, Timestamp):
    """Many-to-many model for Identifier and Group."""

    __tablename__ = 'identifier2group'
    __table_args__ = (
        PrimaryKeyConstraint('identifier_id', 'group_id',
                             name='pk_identifier2group'),
    )
    identifier_id = Column(UUIDType, ForeignKey(Identifier.id,
                                                ondelete='CASCADE',
                                                onupdate='CASCADE'),
                           nullable=False)
    group_id = Column(UUIDType, ForeignKey(Group.id, ondelete='CASCADE',
                                           onupdate='CASCADE'),
                      nullable=False)

    # DB relationships
    identifier = orm_relationship(Identifier, foreign_keys=[identifier_id],
                                  backref='id2groups')
    group = orm_relationship(Group, foreign_keys=[group_id],
                             backref='id2groups')


class Relationship2GroupRelationship(db.Model, Timestamp):
    """Many-to-many model for Relationship to GroupRelationship."""

    __tablename__ = 'relationship2grouprelationship'
    __table_args__ = (
        PrimaryKeyConstraint('relationship_id', 'group_relationship_id',
                             name='pk_relationship2grouprelationship'),
    )
    relationship_id = Column(UUIDType,
                             ForeignKey(Relationship.id, onupdate='CASCADE',
                                        ondelete='CASCADE'),
                             nullable=False)
    group_relationship_id = Column(UUIDType,
                                   ForeignKey(GroupRelationship.id,
                                              onupdate='CASCADE',
                                              ondelete='CASCADE'),
                                   nullable=False)

    # DB relationships
    relationship = orm_relationship(Relationship,
                                    foreign_keys=[relationship_id])
    group_relationship = orm_relationship(GroupRelationship,
                                          foreign_keys=[group_relationship_id])

    def __repr__(self):
        """String representation of the model."""
        return ('<{self.group_relationship}: {self.relationship}>'
                .format(self=self))


class GroupM2M(db.Model, Timestamp):
    """Many-to-many model for Groups."""

    __tablename__ = 'groupm2m'
    __table_args__ = (
        PrimaryKeyConstraint('group_id', 'subgroup_id',
                             name='pk_groupm2m'),
    )
    group_id = Column(UUIDType, ForeignKey(Group.id, onupdate='CASCADE',
                                           ondelete='CASCADE'),
                      nullable=False)
    subgroup_id = Column(UUIDType, ForeignKey(Group.id, onupdate='CASCADE',
                                              ondelete='CASCADE'),
                         nullable=False)

    group = orm_relationship(Group, foreign_keys=[group_id])
    subgroup = orm_relationship(Group, foreign_keys=[subgroup_id])

    def __repr__(self):
        """String representation of the model."""
        return '<{self.group}: {self.subgroup}>'.format(self=self)


class GroupRelationshipM2M(db.Model, Timestamp):
    """Many-to-many model for Group Relationships."""

    __tablename__ = 'grouprelationshipm2m'
    __table_args__ = (
        PrimaryKeyConstraint('relationship_id', 'subrelationship_id',
                             name='pk_grouprelationshipm2m'),
    )
    relationship_id = Column(UUIDType, ForeignKey(GroupRelationship.id,
                                                  onupdate="CASCADE",
                                                  ondelete="CASCADE"),
                             nullable=False)
    subrelationship_id = Column(UUIDType, ForeignKey(GroupRelationship.id,
                                                     onupdate="CASCADE",
                                                     ondelete="CASCADE"),
                                nullable=False)

    relationship = orm_relationship(GroupRelationship,
                                    foreign_keys=[relationship_id])
    subrelationship = orm_relationship(GroupRelationship,
                                       foreign_keys=[subrelationship_id])

    def __repr__(self):
        """String representation of the model."""
        return ('<{self.relationship}: {self.subrelationship}>'
                .format(self=self))


COMMON_SCHEMA_DEFINITIONS = SCHOLIX_SCHEMA['definitions']
OBJECT_TYPE_SCHEMA = COMMON_SCHEMA_DEFINITIONS['ObjectType']
OVERRIDABLE_KEYS = {'Type', 'Title', 'Creator', 'PublicationDate', 'Publisher'}


class GroupMetadata(db.Model, Timestamp):
    """Metadata for a group."""

    __tablename__ = 'groupmetadata'

    # TODO: assert group.type == GroupType.Identity
    group_id = Column(
        UUIDType,
        ForeignKey(Group.id, onupdate='CASCADE', ondelete='CASCADE'),
        primary_key=True)
    group = orm_relationship(
        Group,
        backref=backref('data', uselist=False),
        single_parent=True,
    )
    json = Column(
        JSON()
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
            if k in OVERRIDABLE_KEYS
        },
    }

    def update(self, payload, validate=True):
        """Update the metadata of a group."""
        new_json = deepcopy(self.json or {})
        for k in OVERRIDABLE_KEYS:
            if payload.get(k):
                new_json[k] = payload[k]
        if validate:
            jsonschema.validate(new_json, self.SCHEMA)
        self.json = new_json
        flag_modified(self, 'json')
        return self


class GroupRelationshipMetadata(db.Model, Timestamp):
    """Metadata for a group relationship."""

    __tablename__ = 'grouprelationshipmetadata'

    # TODO: assert group_relationship.type == GroupType.Identity
    group_relationship_id = Column(
        UUIDType,
        ForeignKey(GroupRelationship.id,
                   onupdate='CASCADE',
                   ondelete='CASCADE'),
        primary_key=True)
    group_relationship = orm_relationship(
        GroupRelationship,
        backref=backref('data', uselist=False),
        single_parent=True,
    )
    json = Column(
        JSON()
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

    def update(self, payload, validate=True, multi=False):
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
