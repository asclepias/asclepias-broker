import random
import timeit
from contextlib import contextmanager
from datetime import datetime, timedelta
from uuid import uuid4

from elasticsearch_dsl import Date, DocType, Index, InnerObjectWrapper, \
    Keyword, MetaField, Nested, Object, Q, String, connections
from faker import Faker

es_client = connections.connections.create_connection(hosts=['localhost'], timeout=20)

objects_index = Index('objects')
objects_index.settings(number_of_shards=1, number_of_replicas=0)


class BaseDoc(DocType):

    class Meta(object):
        all = MetaField(enabled=False)
        dynamic = MetaField(False)

    @classmethod
    def get_or_create(cls, id_, **kwargs):
        doc = cls.get(id_, ignore=404)
        if not doc:
            doc = cls(meta={'id': id_}, **kwargs)
            doc.save()
        return doc

    @classmethod
    def all(cls):
        return cls.search().scan()


class IdentifierType(Nested):

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('doc_class', InnerObjectWrapper)
        kwargs.setdefault('properties', {}).update(
            id=Keyword(),
            scheme=Keyword(),
            # scheme_url=Keyword(),
        )
        super().__init__(*args, **kwargs)


class PersonOrOrgBaseType(Object):

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('doc_class', InnerObjectWrapper)
        kwargs.setdefault('properties', {}).update(
            name=String(),
            identifiers=IdentifierType(multi=True),
        )
        super().__init__(*args, **kwargs)


class CreatorType(PersonOrOrgBaseType):
    pass


class ProviderType(PersonOrOrgBaseType):
    pass


class RelationshipHistoryType(Object):

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('doc_class', InnerObjectWrapper)
        kwargs.setdefault('properties', {}).update(
            publication_date=Date(),
            provider=ProviderType(),
            license_url=Keyword(),
        )
        super().__init__(*args, **kwargs)


class RelationshipObjectType(Nested):

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('doc_class', InnerObjectWrapper)
        kwargs.setdefault('properties', {}).update(
            id=Keyword(),
            title=String(),
            type=Object(properties={'type': Keyword(), 'subtype': Keyword()}),
            identifiers=IdentifierType(multi=True),
            creator=CreatorType(multi=True),
            license_url=Keyword(),
            publication_date=Date(),
            relationship_history=RelationshipHistoryType(multi=True),
        )
        super().__init__(*args, **kwargs)


class ObjectRelationshipsType(Nested):

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('doc_class', InnerObjectWrapper)
        kwargs.setdefault('properties', {}).update(

        )
        super().__init__(*args, **kwargs)


@objects_index.doc_type
class ObjectType(BaseDoc):

    title = String()
    type = Object(properties={
        'type': Keyword(),
        'subtype': Keyword(),
    })
    identifiers = IdentifierType(multi=True)
    creator = CreatorType(multi=True)
    license_url = Keyword()
    publication_date = Date()
    relationships = Object(properties=dict(
        isCitedBy=RelationshipObjectType(multi=True),
        isSupplementedBy=RelationshipObjectType(multi=True),
        isRelatedTo=RelationshipObjectType(multi=True)
    ))

    @classmethod
    def get_by_identifier(cls, id_value, fields=None):
        q = cls.search().query(
            'nested', path='identifiers',
            query=Q('term', identifiers__id=id_value))
        if fields:
            q = q.source(**fields)
        return next(q[0].scan(), None)


#
# Queries
#
def get_citations(identifier, target_type=None, use_es_filter=True, include_rels=True):
    src_doc = ObjectType.get_by_identifier(identifier, fields={
        'include': ['title', 'creator', 'identifier', 'type', 'relationships.isCitedBy'],
    })
    if 'isCitedBy' in src_doc.relationships:
        citations = src_doc.relationships.isCitedBy
        if target_type:
            citations = [c for c in citations if c.type.name == target_type]
        return citations
    else:
        return []


#
# Utils
#
def create_all():
    objects_index.create(ignore=[400, 404])


def delete_all():
    objects_index.delete(ignore=[400, 404])


@contextmanager
def progressbar(iterable, label, report_every, total_items):
    print(label, report_every, total_items)
    start = datetime.now()
    print(f'{label} started at: {start}')

    def _gen():
        for i, v in enumerate(iterable):
            if i % int(report_every) == 0:
                t = datetime.now()
                d = t - start
                rate = int(i/d.total_seconds()) if d.total_seconds() != 0 else None
                time_left = timedelta(seconds=((total_items - i) / rate)) if rate else '???'
                print(f'[{t}] - {i}...\t({(d)} - {rate or "???"} items/sec - ETA {time_left})')
            yield v
    yield _gen()
    end = datetime.now()
    print(f'{label} finished at: {end}, Total time: {end-start}')


def benchmark_get_citations(N=100, **kwargs):
    ids = [o._id for o in ObjectType.search().source(False).scan()]

    def _f():
        o = ObjectType.get(random.choice(ids))
        return len(get_citations(random.choice([i.id for i in o.identifiers])))
    return min(timeit.Timer(_f).repeat(3, number=N)) / N


#
# Seed data
#
faker = Faker()
OBJECT_TYPES = [
    {'type': 'literature'},
    {'type': 'literature', 'subtype': 'article'},
    {'type': 'literature', 'subtype': 'book'},
    {'type': 'literature', 'subtype': 'journal'},
    {'type': 'literature', 'subtype': 'preprint'},
    {'type': 'dataset'},
    {'type': 'software'},
]
RELATION_TYPES = [
    # {'relation': 'cites', 'inverse_relation': 'isCitedBy'},
    {'relation': 'isCitedBy'},
    # {'relation': 'isSupplementTo', 'inverse_relation': 'isSupplementedBy'},
    {'relation': 'isSupplementedBy'},
    {'relation': 'isRelatedTo', 'inverse_relation': 'isRelatedTo'},
]
PROVIDERS = ['Zenodo', 'ADS', 'INSPIRE']


def _gen_identifier():
    base_value = uuid4()

    ids = [{'id': f'{faker.url()}{base_value.hex}', 'scheme': 'url'}]
    if random.random() > 0.3:  # doi
        ids.append({'id': f'10.5072/{base_value.hex}', 'scheme': 'doi'})
    if random.random() > 0.8:  # second url
        ids.append({'id': f'{faker.url()}{base_value.hex}', 'scheme': 'url'})
    if random.random() > 0.8:  # PMID
        ids.append({'id': f'{base_value.node}', 'scheme': 'pmid'})
    return ids


def _gen_object(names, ids):
    return ObjectType(
        title=faker.sentence(),
        type=random.choice(OBJECT_TYPES),
        identifiers=ids,
        creator=random.choices(names, k=random.randint(1, 5)),
        publication_date=faker.date(),
    )


def _rel_obj_from_obj(obj):
    return dict(
        id=obj._id,
        title=obj.title,
        type=obj.type,
        identifiers=obj.identifiers,
        creator=obj.creator,
        publication_date=obj.publication_date,
    )


def _add_relationship_to_obj(src, trg, rel_type, rel_history):
    relations = getattr(src.relationships, rel_type, [])
    existing = False
    # Find if relationship to target already exists
    for r in relations:
        if trg._id == r.id:
            # Relationship already exists. Add to history
            existing = True
            r.relationship_history.append(rel_history)
    if not existing:  # Create new
        new_rel_obj = _rel_obj_from_obj(trg)
        new_rel_obj['relationship_history'] = [rel_history]
        relations.append(new_rel_obj)
    src.save()


def create_relationship(src, trg, rel_type=None):
    rel_type = rel_type or random.choice(RELATION_TYPES)
    rel_history = {
        'publication_date': faker.date(),
        'provider': {'name': random.choice(PROVIDERS)},
    }
    _add_relationship_to_obj(src, trg, rel_type['relation'], rel_history)
    if 'inverse_relation' in rel_type:
        _add_relationship_to_obj(trg, src, rel_type['inverse_relation'], rel_history)


def seed_data(N=100, init=False):
    if init:
        delete_all()
        create_all()

    names = [{'name': n} for n in {faker.name() for _ in range(N)}]
    id_groups = [_gen_identifier() for _ in range(N)]
    object_ids = [o._id for o in ObjectType.all()]

    with progressbar(id_groups, 'Objects...', len(id_groups)/10, len(id_groups)) as progress:
        for ids in progress:
            obj = _gen_object(names, ids)
            obj.save()
            object_ids.append(obj._id)

    with progressbar(range(N * 100), 'Relationships...', N, N * 100) as progress:
        for _ in progress:
            src_obj = ObjectType.get(random.choice(object_ids))
            trg_obj = ObjectType.get(random.choice(object_ids))
            while trg_obj._id == src_obj._id:
                trg_obj = ObjectType.get(random.choice(object_ids))
            create_relationship(src_obj, trg_obj)


def add_random_citations(obj_ids, src_obj: ObjectType, N=100):
    for _ in range(N):
        trg_obj_id = random.choice(obj_ids)
        while src_obj._id == trg_obj_id:
            trg_obj_id = random.choice(obj_ids)
        trg_obj = ObjectType.get(trg_obj_id)
        create_relationship(src_obj, trg_obj, rel_type={'relation': 'isCitedBy'})
