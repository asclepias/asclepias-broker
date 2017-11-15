# For now this is a toy datastore that is completely unoptimized

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, String, ForeignKey, Integer, Enum

Base = declarative_base()


class Identifier(Base):
    """
    A persistent Identifier
    """
    __tablename__ = 'identifiers'
    id = Column(String, primary_key=True)
    id_schema = Column(String)
    id_url = Column(String)

    def __repr__(self):
        return (f'Identifier: '
                f'id={self.id} '
                f'id_schema={self.id_schema} '
                f'id_url={self.id_url}')


class Type(Base):
    """
    An object type
    """
    __tablename__ = 'types'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    sub_type = Column(String)
    sub_type_schema = Column(String)

    def __repr__(self):
        return (f'Type: '
                f'id={self.id} '
                f'name={self.name} '
                f'sub_type={self.sub_type} '
                f'sub_type_schema={self.sub_type_schema}')


class RelationshipType(Base):
    """
    A relationship type
    """
    __tablename__ = 'relationship_types'
    id = Column(Integer, primary_key=True)
    scholix_relationship = Column(Enum("IsReferencedBy", "References", "IsSupplementTo",
                                "IsSupplementedBy", "IsRelatedTo"))
    original_relationship_name = Column(Enum("IsCitedBy", "Cites", "IsSupplementTo",
                                      "IsSupplementedBy", "IsContinuedBy",
                                      "Continues", "HasMetadata",
                                      "IsMetadataFor" "IsNewVersionOf",
                                      "IsPreviousVersionOf", "IsPartOf",
                                      "HasPart", "IsReferencedBy", "References",
                                      "IsDocumentedBy", "Documents",
                                      "IsCompiledBy", "Compiles",
                                      "IsVariantFormOf", "IsOriginalFormOf",
                                      "IsIdenticalTo", "IsReviewedBy",
                                      "Reviews", "IsDerivedFrom", "IsSourceOf",
                                      "IsDescribedBy", "Describes",
                                      "HasVersion", "IsVersionOf",
                                      "IsRequiredBy", "Requires"))
    original_relationship_schema = Column(Enum("DataCite"))

    def __repr__(self):
        return (f'RelationshipType: '
                f'id={self.id} '
                f'scholix_relationship={self.scholix_relationship} '
                f'original_relationship_name={self.original_relationship_name} '
                f'original_relationship_schema={self.original_relationship_schema}')


class Organization(Base):
    __tablename__ = 'organizations'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    identifier = Column(String, ForeignKey('identifiers.id'))

    def __repr__(self):
        return (f'Organization: '
                f'id={self.id} '
                f'name={self.name} '
                f'identifier={self.identifier}')


class Object(Base):

    __tablename__ = 'objects'

    id = Column(Integer, primary_key=True)

    identifier_id = Column(String, ForeignKey('identifiers.id'))
    type_id = Column(Integer, ForeignKey('types.id'))
    publisher_id = Column(String, ForeignKey('organizations.id'))
    publication_date = Column(String)

    def __repr__(self):
        return (f'Object: '
                f'id={self.id} '
                f'identifier_id={self.identifier_id} '
                f'type_id={self.type_id} '
                f'publisher_id={self.publisher_id} '
                f'publication_date={self.publication_date}')


class Relationship(Base):

    __tablename__ = 'relationships'

    id = Column(Integer, primary_key=True)
    source_id = Column(String, ForeignKey('identifiers.id'))
    target_id = Column(String, ForeignKey('identifiers.id'))
    relationship_type = Column(String, ForeignKey('relationship_types.id'))

    def __repr__(self):
        return (f'Relationship: '
                f'id={self.id} '
                f'source={self.source_id} '
                f'relationship_type={self.relationship_type} '
                f'target={self.target_id}')

    # object1 = relationship("Entity", foreign_keys=[object1_id], back_populates="relationships")
    # object2 = relationship("Entity", foreign_keys=[object2_id], back_populates="relationships")

    # def __repr__(self):
    #     return ("<Relationship(object_1='%s', relationship_type='%s', object_2='%s')>" %
    #             (self.object_1_id, self.relationship_type, self.object_2_id))

# Entity.relationships = relationship("Relationship", order_by=Relationship.id,
#                                     primaryjoin=or_(Entity.id == Relationship.object_1_id, Entity.id == Relationship.object_2_id))
