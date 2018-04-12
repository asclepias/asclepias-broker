# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 CERN.
#
# Asclepias Broker is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

import random
import timeit
from contextlib import contextmanager
from datetime import datetime, timedelta
from uuid import uuid4

from elasticsearch_dsl import Date, DocType, Index, InnerDoc, Keyword, \
    MetaField, Nested, Object, Q, Text, connections
from faker import Faker

from .models import Relation

#
# Config/Setup
#

# TODO: Don't use this...
# Register global client
es_client = connections.connections.create_connection()

objects_index = Index('objects')
objects_index.settings(number_of_shards=1, number_of_replicas=0)
relationships_index = Index('relationships')
relationships_index.settings(number_of_shards=1, number_of_replicas=0)


DB_RELATION_TO_ES = {
    Relation.Cites: ('cites', 'isCitedBy'),
    Relation.IsSupplementTo: ('isSupplementTo', 'isSupplementedBy'),
    Relation.IsRelatedTo: ('isRelatedTo', 'isRelatedTo'),
}


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


@objects_index.doc_type
class ObjectDoc(BaseDoc):

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


@relationships_index.doc_type
class ObjectRelationshipsDoc(BaseDoc):

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


#
# Queries
#
def get_relationships(identifier, scheme=None, relation=None, target_type=None,
                      from_=None, to=None, group_by=None):
    src_doc = ObjectDoc.get_by_identifiers([identifier])
    rels = []
    if src_doc:
        rel_doc = src_doc.relationships()
        rels = rel_doc.rel_objects(
            relation=relation, target_type=target_type, from_=from_, to=to)
    return src_doc, rels


def get_citations(*args, **kwargs):
    return get_relationships(*args, relation='isCitedBy', **kwargs)


#
# Utils
#
def create_all():
    objects_index.create(ignore=[400, 404])
    relationships_index.create(ignore=[400, 404])


def delete_all():
    objects_index.delete(ignore=[400, 404])
    relationships_index.delete(ignore=[400, 404])


@contextmanager
def progressbar(iterable, label, report_every, total_items):
    print(label, report_every, total_items)
    start = datetime.now()
    print('{label} started at: {start}'.format(label=label, start=start))

    def _gen():
        for i, v in enumerate(iterable):
            if i % int(report_every) == 0:
                t = datetime.now()
                d = t - start
                rate = int(i/d.total_seconds()) if d.total_seconds() != 0 else None
                time_left = timedelta(seconds=((total_items - i) / rate)) if rate else '???'
                print('[{t}] - {i}...\t({d} - {rate} items/sec - ETA {time_left})'
                      .format(t=t, i=i, d=d, rate=(rate or "???"), time_left=time_left))
            yield v
    yield _gen()
    end = datetime.now()
    print('{label} finished at: {end}, Total time: {total}'.format(label=label, end=end, total=(end-start)))


def benchmark_get_citations(N=100, **kwargs):
    ids = [o._id for o in ObjectDoc.search().source(False).scan()]

    def _f():
        o = ObjectDoc.get(random.choice(ids))
        return len(get_citations(random.choice([i.ID for i in o.Identifier])))
    return min(timeit.Timer(_f).repeat(3, number=N)) / N


#
# Seed data
#
faker = Faker()
OBJECT_TYPES = [
    {'Name': 'literature'},
    {'Name': 'literature', 'SubType': 'article'},
    {'Name': 'literature', 'SubType': 'book'},
    {'Name': 'literature', 'SubType': 'journal'},
    {'Name': 'literature', 'SubType': 'preprint'},
    {'Name': 'dataset'},
    {'Name': 'software'},
]
RELATION_TYPES = [
    ('cites', 'isCitedBy'),
    ('isCitedBy', 'cites'),
    ('isSupplementTo', 'isSupplementedBy'),
    ('isSupplementedBy', 'isSupplementTo'),
    ('isRelatedTo', 'isRelatedTo'),
]
PROVIDERS = ['Zenodo', 'ADS', 'INSPIRE', 'DLI']


def _gen_identifier():
    base_value = uuid4()
    ids = [{'ID': '{}{}'.format(faker.url(), base_value.hex), 'IDScheme': 'url'}]
    if random.random() > 0.3:  # doi
        ids.append({'ID': '10.5072/{}'.format(base_value.hex), 'IDScheme': 'doi'})
    if random.random() > 0.8:  # second url
        ids.append({'ID': '{}{}'.format(faker.url(), base_value.hex), 'IDScheme': 'url'})
    if random.random() > 0.8:  # PMID
        ids.append({'ID': str(base_value.node), 'IDScheme': 'pmid'})
    return ids


def _gen_object(names, ids):
    return ObjectDoc(
        Title=faker.sentence(),
        Type=random.choice(OBJECT_TYPES),
        Identifier=ids,
        Creator=[random.choice(names) for _ in range(random.randint(1,5))],
        PublicationDate=faker.date(),
    )


def _gen_relationship(source, target, rel_type=None):
    rel_type, inv_rel_type = rel_type or random.choice(RELATION_TYPES)
    provider = random.choice(PROVIDERS)
    publication_date = faker.date()

    src_rels = source.relationships()
    trg_rels = target.relationships()

    new_src_rels = getattr(src_rels, rel_type, [])
    new_src_rels.append({
        'TargetID': target._id,
        'History': [{
            'LinkPublicationDate': publication_date,
            'LinkProvider': {'Name': provider}}
        ]
    })
    src_rels[rel_type] = new_src_rels
    src_rels.save()

    new_trg_rels = getattr(trg_rels, inv_rel_type, [])
    new_trg_rels.append({
        'TargetID': source._id,
        'History': [{
            'LinkPublicationDate': publication_date,
            'LinkProvider': {'Name': provider}}
        ]
    })
    trg_rels[inv_rel_type] = new_trg_rels
    trg_rels.save()

    return src_rels, trg_rels


def seed_data(N=1000):
    delete_all()
    create_all()

    names = [{'Name': n} for n in {faker.name() for _ in range(N)}]
    id_groups = [_gen_identifier() for _ in range(N)]
    object_ids = []

    with progressbar(id_groups, 'Objects...', len(id_groups)/10, len(id_groups)) as progress:
        for ids in progress:
            obj = _gen_object(names, ids)
            obj.save()
            # Index an empty object relationships as well
            rel = ObjectRelationshipsDoc(meta={'id': obj._id})
            rel.save()
            object_ids.append(obj._id)

    with progressbar(range(N * 100), 'Relationships...', N, N * 100) as progress:
        for _ in progress:
            src_obj_id = random.choice(object_ids)
            trg_obj_id = random.choice(object_ids)
            while trg_obj_id == src_obj_id:
                trg_obj_id = random.choice(object_ids)
            src_obj = ObjectDoc.get(src_obj_id)
            trg_obj = ObjectDoc.get(trg_obj_id)

            _gen_relationship(src_obj, trg_obj)


def add_random_citations(objects, trg_obj: ObjectDoc, N=100):
    existing_citations = {c for _, c in trg_obj.Relationships.isCitedBy}
    for _ in range(N):
        src_obj = random.choice(objects)
        while trg_obj._id == src_obj._id or src_obj._id in existing_citations:
            src_obj = random.choice(objects)
        existing_citations.add(src_obj._id)
        rel = _gen_relationship(src_obj, trg_obj,
                                rel_type=RELATION_TYPES[0])  # citation type
        rel.save()

        relations = getattr(src_obj.Relationships, str(rel.RelationshipType.Name), [])
        relations.append({'RelationshipID': rel._id, 'TargetID': trg_obj._id})
        src_obj.Relationships[str(rel.RelationshipType.Name)] = relations
        src_obj.save()
        relations = getattr(trg_obj.Relationships, str(rel.InverseRelation), [])
        relations.append({'RelationshipID': rel._id, 'TargetID': src_obj._id})
        trg_obj.Relationships[str(rel.InverseRelation)] = relations
        trg_obj.save()
