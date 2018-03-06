import operator
import random
import timeit
from contextlib import contextmanager
from datetime import datetime, timedelta
from uuid import uuid4
from .datastore import Relation

from elasticsearch_dsl import Date, DocType, Index, InnerObjectWrapper, \
    Keyword, MetaField, Nested, Object, Q, String, connections
from faker import Faker

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
class IdentifierObject(Nested):

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('doc_class', InnerObjectWrapper)
        kwargs.setdefault('properties', {}).update(
            ID=Keyword(),
            IDScheme=Keyword(),
            IDURL=Keyword(),
        )
        super().__init__(*args, **kwargs)


class PersonOrOrgBaseObject(Nested):

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('doc_class', InnerObjectWrapper)
        kwargs.setdefault('properties', {}).update(
            Name=String(),
            Identifier=IdentifierObject(multi=True),
        )
        super().__init__(*args, **kwargs)


class CreatorTypeObject(PersonOrOrgBaseObject):
    pass


class RelationshipRefTypeObject(Object):

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('doc_class', InnerObjectWrapper)
        kwargs.setdefault('properties', {}).update(
            RelationshipID=Keyword(),
            TargetID=Keyword(),
        )
        super().__init__(*args, **kwargs)


class ObjectRelationshipsType(Object):

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('doc_class', InnerObjectWrapper)
        kwargs.setdefault('properties', {}).update(
            cites=RelationshipRefTypeObject(multi=True),
            isCitedBy=RelationshipRefTypeObject(multi=True),
            isSupplementTo=RelationshipRefTypeObject(multi=True),
            isSupplementedBy=RelationshipRefTypeObject(multi=True),
            isRelatedTo=RelationshipRefTypeObject(multi=True),
        )
        super().__init__(*args, **kwargs)


@objects_index.doc_type
class ObjectDoc(BaseDoc):

    Title = String()
    Type = Object(properties=dict(
        Type=Keyword(),
        SubType=Keyword(),
        SubTypeSchema=Keyword(),
    ))
    Identifier = IdentifierObject(multi=True)
    Creator = CreatorTypeObject(multi=True)
    PublicationDate = Date()
    Publisher = CreatorTypeObject(multi=True)
    Relationships = ObjectRelationshipsType(multi=False)

    @classmethod
    def get_by_identifiers(cls, id_values, _source=None):
        q = (cls.search()
             .query('nested',
                    path='Identifier',
                    query=Q('terms', Identifier__ID=id_values)))
        if _source:
            q = q.source(_source)
        return next(q[0].scan(), None)


class ProviderObject(PersonOrOrgBaseObject):
    pass


class RelationshipHistoryObject(Nested):

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('doc_class', InnerObjectWrapper)
        kwargs.setdefault('properties', {}).update(
            LinkPublicationDate=Date(),
            LinkProvider=ProviderObject(multi=True),
            LicenseURL=Keyword(),
        )
        super().__init__(*args, **kwargs)


@relationships_index.doc_type
class RelationshipDoc(BaseDoc):

    SourceID = Keyword()
    TargetID = Keyword()
    RelationshipType = Object(properties=dict(
        Name=Keyword(),
        SubType=Keyword(),
        SubTypeSchema=Keyword(),
    ))
    InverseRelation = Keyword()
    History = RelationshipHistoryObject(multi=True)


#
# Queries
#
def get_citations(identifier, target_type=None, use_es_filter=False):
    src_doc = ObjectDoc.get_by_identifiers([identifier], _source=[
        'Title', 'Creator', 'Identifier', 'Type', 'Relationships.isCitedBy'])
    if 'isCitedBy' in src_doc.Relationships:
        rel_trg_getter = operator.itemgetter('RelationshipID', 'TargetID')
        rels, targets = zip(*map(rel_trg_getter,
                                 src_doc.Relationships.isCitedBy))
        rel_docs = RelationshipDoc.mget(rels)
        if target_type:
            if use_es_filter:
                # TODO: Fix this verision
                trg_docs = (
                    ObjectDoc.search()
                    .source(exclude=['Relationships'])
                    .query('ids', values=targets)
                    .query('term', **{'Type.Name': target_type})).scan()
            else:
                trg_docs = ObjectDoc.mget(
                    targets, _source_exclude=['Relationships'])
                trg_docs = [d if d.Type.Name == target_type else None
                            for d in trg_docs]
        else:
            trg_docs = ObjectDoc.mget(
                targets, _source_exclude=['Relationships'])
        return src_doc, list(zip(rel_docs, trg_docs))
    else:
        return []


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
    {'RelationshipType': {'Name': 'cites'}, 'InverseRelation': 'isCitedBy'},
    {'RelationshipType': {'Name': 'isCitedBy'}, 'InverseRelation': 'cites'},
    {'RelationshipType': {'Name': 'isSupplementTo'}, 'InverseRelation': 'isSupplementedBy'},
    {'RelationshipType': {'Name': 'isSupplementedBy'}, 'InverseRelation': 'isSupplementTo'},
    {'RelationshipType': {'Name': 'isRelatedTo'}, 'InverseRelation': 'isRelatedTo'},
]
PROVIDERS = ['Zenodo', 'ADS', 'INSPIRE']


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
    kwargs = {
        'SourceID': source._id,
        'TargetID': target._id,
    }
    kwargs.update(rel_type or random.choice(RELATION_TYPES))
    kwargs['History'] = [
        {'PublicationDate': faker.date(), 'Provider': {'Name': random.choice(PROVIDERS)}}
        for _ in range(random.randint(1,3))]
    return RelationshipDoc(**kwargs)


def seed_data(N=1000):
    delete_all()
    create_all()

    names = [{'Name': n} for n in {faker.name() for _ in range(N)}]
    id_groups = [_gen_identifier() for _ in range(N)]
    objects = []

    with progressbar(id_groups, 'Objects...', len(id_groups)/10, len(id_groups)) as progress:
        for ids in progress:
            obj = _gen_object(names, ids)
            obj.save()
            objects.append(obj)

    with progressbar(range(N * 100), 'Relationships...', N, N * 100) as progress:
        for _ in progress:
            src_obj = random.choice(objects)
            trg_obj = random.choice(objects)
            while trg_obj._id == src_obj._id:
                trg_obj = random.choice(objects)

            rel = _gen_relationship(src_obj, trg_obj)
            rel.save()

            # TODO; Maybe order, for easyier "zipping" in `get_cittations`?
            relations = getattr(src_obj.Relationships, str(rel.RelationshipType.Name), [])
            relations.append({'RelationshipID': rel._id, 'TargetID': trg_obj._id})
            src_obj.Relationships[str(rel.RelationshipType.Name)] = relations
            src_obj.save()

            relations = getattr(trg_obj.Relationships, str(rel.InverseRelation), [])
            relations.append({'RelationshipID': rel._id, 'TargetID': src_obj._id})
            trg_obj.Relationships[str(rel.InverseRelation)] = relations
            trg_obj.save()


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
