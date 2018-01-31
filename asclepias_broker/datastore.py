# For now this is a toy datastore that is completely unoptimized

import enum
import uuid

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, String, ForeignKey, Integer, Enum, JSON, Boolean
from sqlalchemy.types import DateTime
from sqlalchemy_utils.types import UUIDType, JSONType
from sqlalchemy_utils.models import Timestamp
from sqlalchemy.schema import PrimaryKeyConstraint, UniqueConstraint, Index
from sqlalchemy.orm import relationship as orm_relationship

Base = declarative_base()


class Relation(enum.Enum):
    Cites = 1
    IsSupplementTo = 2
    HasVersion = 3
    IsIdenticalTo = 4
    IsRelatedTo = 5


class EventType(enum.Enum):
    RelationshipCreated = 1
    RelationshipDeleted = 2


class PayloadType(enum.Enum):
    Relationship = 1
    Identifier = 2


class GroupType(enum.Enum):
    Identity = 1
    Version = 2


class Identifier(Base, Timestamp):
    """A persistent Identifier."""

    __tablename__ = 'identifier'
    __table_args__ = (
        UniqueConstraint('value', 'scheme', name='uq_identifier_value_scheme'),
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
    def get(cls, session, value=None, scheme=None, **kwargs):
        """Get the identifier from the database."""
        return session.query(cls).filter_by(
            value=value, scheme=scheme).one_or_none()

    def fetch_or_create_id(self, session):
        if not self.id:
            obj = self.get(session, self.value, self.scheme)
            if obj:
                self = obj
            else:
                self.id = uuid.uuid4()
        return self

    def _get_related(self, session, condition, relationship, with_deleted=False):
        cond = condition & (Relationship.relation == relationship)
        if not with_deleted:
            cond &= (Relationship.deleted == False)
        return session.query(Relationship).filter(cond)

    def _get_identities(self, session, as_relation=False):
        """Get the first-layer of 'Identical' Identifies."""
        cond = ((Relationship.source == self) | (Relationship.target == self))
        q = self._get_related(session, cond, Relation.IsIdenticalTo)
        if as_relation:
            return q.all()
        else:
            siblings = set(sum([[item.source, item.target] for item in q], []))
            if siblings:
                return list(siblings)
            else:
                return [self, ]

    def get_identities(self, session):
        """Get the fully-expanded list of 'Identical' Identifiers."""
        ids = next_ids = set([self])
        while next_ids:
            grp = set(sum([item._get_identities(session) for item in next_ids], []))
            next_ids = grp - ids
            ids |= grp
        return list(ids)

    def get_parents(self, session, rel_type, as_relation=False):
        """Get all parents of given Identifier for given relation."""
        q = self._get_related(session, (Relationship.target == self), rel_type)
        if as_relation:
            return q.all()
        else:
            return [item.source for item in q]

    def get_children(self, session, rel_type, as_relation=False):
        """Get all children of given Identifier for given relation."""
        q = self._get_related(session, (Relationship.source == self), rel_type)
        if as_relation:
            return q.all()
        else:
            return [item.target for item in q]


class Relationship(Base, Timestamp):
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
    def get(cls, session, source, target, relation, **kwargs):
        return session.query(cls).filter_by(
            source_id=source.id, target_id=target.id,
            relation=relation).one_or_none()

    def fetch_or_create_id(self, session):
        self.source = self.source.fetch_or_create_id(session)
        self.target = self.target.fetch_or_create_id(session)

        if not self.id:
            obj = self.get(session, self.source, self.target, self.relation)
            if obj:
                self = obj
            else:
                self.id = uuid.uuid4()
        return self

    def __repr__(self):
        return "<{self.source.value} {self.relation.name} {self.target.value}{deleted}>".format(self=self, deleted=" [D]" if self.deleted else "")


class Event(Base, Timestamp):
    __tablename__ = 'event'

    id = Column(UUIDType, primary_key=True)
    description = Column(String, nullable=True)
    event_type = Column(Enum(EventType))
    creator = Column(String)
    source = Column(String)
    payload = Column(JSONType)
    time = Column(DateTime)

    @classmethod
    def get(cls, session, id=None, **kwargs):
        return session.query(cls).filter_by(id=id).one_or_none()

    def __repr__(self):
        """String representation of the Identifier."""
        return "<{self.id}: {self.time}>".format(self=self)


class ObjectEvent(Base, Timestamp):
    __tablename__ = 'objectevent'
    __table_args__ = (
        PrimaryKeyConstraint('event_id', 'object_uuid', 'payload_type',
                             'payload_index', name='pk_objectevent'),
    )

    event_id = Column(UUIDType, ForeignKey(Event.id), nullable=False)
    object_uuid = Column(UUIDType, nullable=False)
    payload_type = Column(Enum(PayloadType), nullable=False)
    payload_index = Column(Integer, nullable=False)

    def __repr__(self):
        """String representation of the Identifier."""
        return "<{self.event_id}: {self.object_uuid}>".format(self=self)


class Group(Base, Timestamp):
    __tablename__ = 'group'

    id = Column(UUIDType, default=uuid.uuid4, primary_key=True)
    type = Column(Enum(GroupType), nullable=False)

    def __repr__(self):
        """String representation of the Identifier."""
        return "<{self.id}: {self.type.name}>".format(self=self)

class GroupRelationship(Base, Timestamp):
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
    source = orm_relationship(Group, foreign_keys=[source_id],
        backref='sources')
    target = orm_relationship(Group, foreign_keys=[target_id],
        backref='targets')
    # TODO:
    # We don't store 'deleted' as in the relation as most likely don't need
    # that as 'ground truth' in precomputed groups anyway

    def __repr__(self):
        return "<{self.source} {self.relation.name} {self.target}>".format(self=self)

class Identifier2Group(Base, Timestamp):
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


class Relationship2GroupRelationship(Base, Timestamp):
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
        return "<{self.group_relationship}: {self.relationship}>".format(self=self)

class GroupM2M(Base, Timestamp):
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
        return "<{self.group}: {self.subgroup}>".format(self=self)

class GroupRelationshipM2M(Base, Timestamp):
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
        return "<{self.relationship}: {self.subrelationship}>".format(self=self)
