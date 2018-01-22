# For now this is a toy datastore that is completely unoptimized

import enum
import uuid

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, String, ForeignKey, Integer, Enum, JSON
from sqlalchemy_utils.types import UUIDType, JSONType
from sqlalchemy.orm import relationship

Base = declarative_base()



class RelationshipType(enum.Enum):
    Cites = 1
    IsSupplementTo = 2
    HasVersion = 3
    IsIdenticalTo = 4
    IsRelatedTo = 5


class Identifier(Base):
    """A persistent Identifier."""

    __tablename__ = 'identifier'
    # TODO Maybe separate ID and UUID into two columns for better indexing
    id = Column(UUIDType, default=uuid.uuid4, primary_key=True)
    value = Column(String)
    scheme = Column(String)

    def __repr__(self):
        return (f'Identifier: '
                f'id={self.id} '
                f'scheme={self.scheme} '
                f'value={self.value}')


    def get_identities(self, session):
        q =  (
            session.query(Relationship)
            .filter(((Relationship.source == self) | (Relationship.target == self))
                    & (Relationship.relationship_type == RelationshipType.IsIdenticalTo)))
        siblings = sum([[item.source_id, item.target_id] for item in q], [])
        if not siblings:
            return [self, ]
        return [session.query(Identifier).get(uuid) for uuid in set(siblings)]

    def get_parents(self, session, relation_type=RelationshipType.Cites):
        q =  (
            session.query(Relationship)
            .filter((Relationship.target == self)
                    & (Relationship.relationship_type == relation_type)))
        parents = [item.source_id for item in q]
        return [session.query(Identifier).get(uuid) for uuid in set(parents)]


    def get_children(self, session, relation_type=RelationshipType.Cites):
        q =  (
            session.query(Relationship)
            .filter((Relationship.source == self)
                    & (Relationship.relationship_type == relation_type)))
        children = [item.target_id for item in q]
        return [session.query(Identifier).get(uuid) for uuid in set(children)]


class Relationship(Base):

    __tablename__ = 'relationship'

    id = Column(UUIDType, default=uuid.uuid4, primary_key=True)
    source_id = Column(UUIDType, ForeignKey(Identifier.id))
    target_id = Column(UUIDType, ForeignKey(Identifier.id))
    relationship_type = Column(Enum(RelationshipType))

    source = relationship(Identifier, foreign_keys=[source_id], backref='sources')
    target = relationship(Identifier, foreign_keys=[target_id], backref='targets')

    def __repr__(self):
        return (f'Relationship: '
                f'id={self.id} '
                f'source={self.source.value} '
                f'relationship_type={self.relationship_type} '
                f'target={self.target.value}')
