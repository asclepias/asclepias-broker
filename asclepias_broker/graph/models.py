# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 CERN.
#
# Asclepias Broker is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
"""Graph database models."""

import enum
import uuid

from invenio_db import db
from sqlalchemy.schema import Index, PrimaryKeyConstraint, UniqueConstraint
from sqlalchemy_utils.models import Timestamp
from sqlalchemy_utils.types import UUIDType

from ..core.models import Identifier, Relation, Relationship


class GroupType(enum.Enum):
    """Group type."""

    Identity = 1
    Version = 2


class Group(db.Model, Timestamp):
    """Group model."""

    __tablename__ = 'group'

    id = db.Column(UUIDType, default=uuid.uuid4, primary_key=True)
    type = db.Column(db.Enum(GroupType), nullable=False)

    identifiers = db.relationship(
        Identifier,
        secondary=lambda: Identifier2Group.__table__,
        backref='groups',
        viewonly=True)

    groups = db.relationship(
        'Group',
        secondary=lambda: GroupM2M.__table__,
        primaryjoin=lambda: (Group.id == GroupM2M.group_id),
        secondaryjoin=lambda: (Group.id == GroupM2M.subgroup_id))

    def __repr__(self):
        """String representation of the group."""
        return f"<{self.id}: {self.type.name}>"


class GroupRelationship(db.Model, Timestamp):
    """Group relationship model."""

    __tablename__ = 'grouprelationship'
    __table_args__ = (
        UniqueConstraint('source_id', 'target_id', 'relation',
                         name='uq_grouprelationship_source_target_relation'),
        # TODO: Change to "index=True"
        Index('ix_grouprelationship_source', 'source_id'),
        Index('ix_grouprelationship_target', 'target_id'),
        Index('ix_grouprelationship_relation', 'relation'),
    )

    id = db.Column(UUIDType, default=uuid.uuid4, primary_key=True)
    type = db.Column(db.Enum(GroupType), nullable=False)
    relation = db.Column(db.Enum(Relation), nullable=False)
    source_id = db.Column(
        UUIDType,
        db.ForeignKey(Group.id, ondelete='CASCADE', onupdate='CASCADE'),
        nullable=False
    )
    target_id = db.Column(
        UUIDType,
        db.ForeignKey(Group.id, ondelete='CASCADE', onupdate='CASCADE'),
        nullable=False
    )

    # DB relationships
    source = db.relationship(
        Group, foreign_keys=[source_id], backref='sources')
    target = db.relationship(
        Group, foreign_keys=[target_id], backref='targets')

    relationships = db.relationship(
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
        return f'<{self.source} {self.relation.name} {self.target}>'


class Identifier2Group(db.Model, Timestamp):
    """Many-to-many model for Identifier and Group."""

    __tablename__ = 'identifier2group'
    __table_args__ = (
        PrimaryKeyConstraint('identifier_id', 'group_id',
                             name='pk_identifier2group'),
    )
    identifier_id = db.Column(
        UUIDType,
        db.ForeignKey(Identifier.id, ondelete='CASCADE', onupdate='CASCADE'),
        nullable=False
    )
    group_id = db.Column(
        UUIDType,
        db.ForeignKey(Group.id, ondelete='CASCADE', onupdate='CASCADE'),
        nullable=False
    )

    # DB relationships
    identifier = db.relationship(
        Identifier, foreign_keys=[identifier_id], backref='id2groups')
    group = db.relationship(
        Group, foreign_keys=[group_id], backref='id2groups')


class Relationship2GroupRelationship(db.Model, Timestamp):
    """Many-to-many model for Relationship to GroupRelationship."""

    __tablename__ = 'relationship2grouprelationship'
    __table_args__ = (
        PrimaryKeyConstraint('relationship_id', 'group_relationship_id',
                             name='pk_relationship2grouprelationship'),
    )
    relationship_id = db.Column(
        UUIDType,
        db.ForeignKey(Relationship.id, onupdate='CASCADE', ondelete='CASCADE'),
        nullable=False
    )
    group_relationship_id = db.Column(
        UUIDType,
        db.ForeignKey(
            GroupRelationship.id, onupdate='CASCADE', ondelete='CASCADE'),
        nullable=False)

    # DB relationships
    relationship = db.relationship(
        Relationship, foreign_keys=[relationship_id],
        backref='relationship2group_relationship')
    group_relationship = db.relationship(
        GroupRelationship, foreign_keys=[group_relationship_id],
        backref='relationship2group_relationship')

    def __repr__(self):
        """String representation of the model."""
        return f'<{self.group_relationship}: {self.relationship}>'


class GroupM2M(db.Model, Timestamp):
    """Many-to-many model for Groups."""

    __tablename__ = 'groupm2m'
    __table_args__ = (
        PrimaryKeyConstraint('group_id', 'subgroup_id', name='pk_groupm2m'),
        UniqueConstraint('subgroup_id', name='uq_groupm2m_subgroup_id'),
    )
    group_id = db.Column(
        UUIDType,
        db.ForeignKey(Group.id, onupdate='CASCADE', ondelete='CASCADE'),
        nullable=False
    )
    subgroup_id = db.Column(
        UUIDType,
        db.ForeignKey(Group.id, onupdate='CASCADE', ondelete='CASCADE'),
        nullable=False
    )
    group = db.relationship(
        Group, foreign_keys=[group_id], backref='subgroupsm2m')
    subgroup = db.relationship(
        Group, foreign_keys=[subgroup_id], backref='supergroupsm2m')

    def __repr__(self):
        """String representation of the model."""
        return f'<{self.group}: {self.subgroup}>'


class GroupRelationshipM2M(db.Model, Timestamp):
    """Many-to-many model for Group Relationships."""

    __tablename__ = 'grouprelationshipm2m'
    __table_args__ = (
        PrimaryKeyConstraint('relationship_id', 'subrelationship_id',
                             name='pk_grouprelationshipm2m'),
    )
    relationship_id = db.Column(
        UUIDType,
        db.ForeignKey(
            GroupRelationship.id, onupdate="CASCADE", ondelete="CASCADE"),
        nullable=False
    )
    subrelationship_id = db.Column(
        UUIDType,
        db.ForeignKey(
            GroupRelationship.id, onupdate="CASCADE", ondelete="CASCADE"),
        nullable=False
    )

    relationship = db.relationship(
        GroupRelationship,
        foreign_keys=[relationship_id],
        backref='subrelationshipsm2m')
    subrelationship = db.relationship(
        GroupRelationship,
        foreign_keys=[subrelationship_id],
        backref='superrelationshipsm2m')

    def __repr__(self):
        """String representation of the model."""
        return f'<{self.relationship}: {self.subrelationship}>'
