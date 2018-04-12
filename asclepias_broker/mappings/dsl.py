# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 CERN.
#
# Asclepias Broker is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

from elasticsearch_dsl import Date, DocType, InnerDoc, Keyword, MetaField, \
    Nested, Object, Q, Text
from elasticsearch_dsl.connections import connections
from invenio_search import current_search_client

from ..models import Relation

DB_RELATION_TO_ES = {
    Relation.Cites: ('cites', 'isCitedBy'),
    Relation.IsSupplementTo: ('isSupplementTo', 'isSupplementedBy'),
    Relation.IsRelatedTo: ('isRelatedTo', 'isRelatedTo'),
}


# TODO: Find a way to avoid this... maybe something in ``invenio_search.ext``?
connections.add_connection('default', current_search_client)


class BaseDoc(DocType):

    class Meta(object):
        all = MetaField(enabled=False)
        dynamic = MetaField(False)

    @classmethod
    def all(cls):
        return list(cls.search().scan())


#
# Mappings
#
class IdentifierObject(InnerDoc):

    ID = Keyword()
    IDScheme = Keyword()
    IDURL = Keyword()


class PersonOrOrgBaseObject(InnerDoc):

    Name = Text()
    Identifier = Nested(IdentifierObject, multi=True)


class ObjectType(InnerDoc):

    Type = Keyword()
    SubType = Keyword()
    SubTypeSchema = Keyword()


class ObjectDoc(BaseDoc):

    class Meta:
        index = 'objects'

    Title = Text()
    Type = Object(ObjectType, multi=False)
    Identifier = Nested(IdentifierObject, multi=True)
    Creator = Nested(PersonOrOrgBaseObject, multi=True)
    PublicationDate = Date()
    Publisher = Nested(PersonOrOrgBaseObject, multi=True)

    @classmethod
    def get_by_identifiers(cls, id_values, _source=None):
        q = (cls.search()
             .query('nested',
                    path='Identifier',
                    query=Q('terms', Identifier__ID=id_values)))
        if _source:
            q = q.source(_source)
        return next(q[0].scan(), None)

    def relationships(self, _source=None):
        return ObjectRelationshipsDoc.get(self._id, _source=_source)


class RelationshipHistoryObject(InnerDoc):

    LinkPublicationDate = Date()
    LinkProvider = Nested(PersonOrOrgBaseObject, multi=False)
    LicenseURL = Keyword()


class RelationshipObject(InnerDoc):

    TargetID = Keyword()
    History = Nested(RelationshipHistoryObject, multi=True)


class ObjectRelationshipsDoc(BaseDoc):

    class Meta:
        index = 'relationships'

    cites = Nested(RelationshipObject, multi=True)
    isCitedBy = Nested(RelationshipObject, multi=True)
    isSupplementTo = Nested(RelationshipObject, multi=True)
    isSupplementedBy = Nested(RelationshipObject, multi=True)
    isRelatedTo = Nested(RelationshipObject, multi=True)

    @property
    def object(self):
        return ObjectDoc.get(self.SourceID)

    def rel_objects(self, relation, target_type=None, from_=None, to=None):
        rels = getattr(self, relation, None)
        if rels:
            histories = {r.TargetID: r.to_dict()['History'] for r in rels}
            if target_type:
                objects = (
                    ObjectDoc.search()
                    .query('ids', values=histories.keys())
                    .query('term', **{'Type.Name': target_type})).scan()
            else:
                objects = ObjectDoc.mget(histories.keys())
            return [(o, histories[o._id]) for o in objects]
        return []
