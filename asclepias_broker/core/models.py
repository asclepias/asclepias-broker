# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 CERN.
# Copyright (c) 2017 Thomas P. Robitaille.
#
# Asclepias Broker is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
"""Core database models."""

import enum
import uuid

from invenio_db import db
from sqlalchemy.schema import Index, UniqueConstraint
from sqlalchemy_utils.models import Timestamp
from sqlalchemy_utils.types import UUIDType


class Relation(enum.Enum):
    """Relation type."""

    Cites = 1
    IsSupplementTo = 2
    HasVersion = 3
    IsIdenticalTo = 4
    IsRelatedTo = 5


class Identifier(db.Model, Timestamp):
    """Identifier model."""

    __tablename__ = 'identifier'
    __table_args__ = (
        UniqueConstraint('value', 'scheme',
                         name='uq_identifier_value_scheme'),
        # TODO: Check if equivalent with passing "index=True"
        # Index('ix_identifier_value', 'value'),
        # Index('ix_identifier_scheme', 'scheme'),
    )
    id = db.Column(UUIDType, default=uuid.uuid4, primary_key=True)
    value = db.Column(db.String, index=True)
    scheme = db.Column(db.String, index=True)

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

    def _get_related(self, condition, relationship):
        cond = condition & (Relationship.relation == relationship)
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
        # TODO: See if we can avoid this
        from ..graph.models import GroupType
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

    id = db.Column(UUIDType, default=uuid.uuid4, primary_key=True)
    source_id = db.Column(
        UUIDType,
        db.ForeignKey(Identifier.id,
                      onupdate='CASCADE', ondelete='CASCADE',
                      name='fk_relationship_source'),
        nullable=False
    )
    target_id = db.Column(
        UUIDType,
        db.ForeignKey(Identifier.id,
                      onupdate='CASCADE', ondelete='CASCADE',
                      name='fk_relationship_target'),
        nullable=False
    )
    relation = db.Column(db.Enum(Relation))

    source = db.relationship(Identifier, foreign_keys=[source_id],
                             backref='sources')
    target = db.relationship(Identifier, foreign_keys=[target_id],
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
        # TODO: See if we can avoid this
        from ..graph.models import GroupRelationship, GroupType
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
            '{self.target.value}>'.format(self=self)
        )
