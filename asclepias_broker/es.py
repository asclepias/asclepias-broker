import operator
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
relationships_index = Index('relationships')
relationships_index.settings(number_of_shards=1, number_of_replicas=0)


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
        return list(cls.search().scan())


class IdentifierType(Nested):

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('doc_class', InnerObjectWrapper)
        kwargs.setdefault('properties', {}).update(
            id=Keyword(),
            scheme=Keyword(),
            scheme_url=Keyword(),
        )
        super().__init__(*args, **kwargs)


class PersonOrOrgBaseType(Nested):

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('doc_class', InnerObjectWrapper)
        kwargs.setdefault('properties', {}).update(
            name=String(),
            identifiers=IdentifierType(multi=True),
        )
        super().__init__(*args, **kwargs)


class CreatorType(PersonOrOrgBaseType):
    pass


class RelationshipRefType(Nested):

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('doc_class', InnerObjectWrapper)
        kwargs.setdefault('properties', {}).update(
            relationship_id=Keyword(),
            target_id=Keyword(),
        )
        super().__init__(*args, **kwargs)


class ObjectRelationshipsType(Nested):

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('doc_class', InnerObjectWrapper)
        kwargs.setdefault('properties', {}).update(
            cites=RelationshipRefType(multi=True),
            isCitedBy=RelationshipRefType(multi=True),
            isSupplementTo=RelationshipRefType(multi=True),
            isSupplementedBy=RelationshipRefType(multi=True),
            isRelatedTo=RelationshipRefType(multi=True),
        )
        super().__init__(*args, **kwargs)


@objects_index.doc_type
class ObjectType(BaseDoc):

    title = String()
    type = Object(properties={
        'type': Keyword(),
        'subtype': Keyword(),
        # 'subtype_schema': Keyword(),
    })
    identifiers = IdentifierType(multi=True)
    creator = CreatorType(multi=True)
    license_url = Keyword()
    publication_date = Date()
    relationships = ObjectRelationshipsType(multi=False)

    @classmethod
    def get_by_identifier(cls, id_value, fields=None):
        q = cls.search().query(
            'nested', path='identifiers',
            query=Q('term', identifiers__id=id_value))
        # if fields:
        #     q = q.source(include=['*', 'relations'], exclude=["user.*"])
        return next(q[0].scan(), None)


class ProviderType(PersonOrOrgBaseType):
    pass


class RelationshipHistoryType(Nested):

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('doc_class', InnerObjectWrapper)
        kwargs.setdefault('properties', {}).update(
            publication_date=Date(),
            provider=ProviderType(),
            license_url=Keyword(),
        )
        super().__init__(*args, **kwargs)


@relationships_index.doc_type
class RelationshipType(BaseDoc):

    source = Keyword()
    target = Keyword()
    relation = Keyword()
    inverse_relation = Keyword()
    history = RelationshipHistoryType(multi=True)


#
# Queries
#
def get_citations(identifier, target_type=None, use_es_filter=True, include_rels=True):
    src_doc = ObjectType.get_by_identifier(identifier)
    if 'isCitedBy' in src_doc.relationships:
        rel_trg_getter = operator.itemgetter('relationship_id', 'target_id')
        rels, targets = zip(*map(rel_trg_getter,
                                 src_doc.relationships.isCitedBy))
        rel_docs = RelationshipType.mget(rels) if include_rels else rels
        if target_type:
            if use_es_filter:
                q = (ObjectType.search()
                     .source(exclude=["relationships"])
                     .query('ids', values=targets)
                     .query('term', **{'type.name': target_type}))
                target_docs = q.scan()
            else:
                # TODO: Benchmark in-memory filtering vs ES query filtering
                target_docs = [o for o in ObjectType.mget(targets)
                               if o.type.name == target_type]
        else:
            q = (ObjectType.search()
                 .source(exclude=["relationships"])
                 .query('ids', values=targets))
            target_docs = q.scan()
        return list(zip(rel_docs, target_docs))
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
    objects = ObjectType.all()

    def _f(**kwargs):
        obj = random.choice(objects)
        obj_id = random.choice(obj.identifiers).id
        return len(get_citations(obj_id, **kwargs))
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
    {'relation': 'cites', 'inverse_relation': 'isCitedBy'},
    {'relation': 'isCitedBy', 'inverse_relation': 'cites'},
    {'relation': 'isSupplementTo', 'inverse_relation': 'isSupplementedBy'},
    {'relation': 'isSupplementedBy', 'inverse_relation': 'isSupplementTo'},
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


def _gen_relationship(source, target, rel_type=None):
    kwargs = {
        'source': source._id,
        'target': target._id,
    }
    rel_type = rel_type or random.choice(RELATION_TYPES)
    kwargs.update(rel_type)
    kwargs['history'] = [
        {'publication_date': faker.date(), 'provider': {'name': p}}
        for p in random.choices(PROVIDERS, k=random.randint(1, 3))]
    return RelationshipType(**kwargs)


def seed_data(N=1000):
    delete_all()
    create_all()

    names = [{'name': n} for n in {faker.name() for _ in range(N)}]
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

            relations = getattr(src_obj.relationships, str(rel.relation), [])
            relations.append({'relationship_id': rel._id, 'target_id': trg_obj._id})
            src_obj.relationships[str(rel.relation)] = relations
            src_obj.save()
            # TODO: Investigate using update API
            # src_obj.update(**{f'relationships.{rel.relation}': relations})

            relations = getattr(trg_obj.relationships, str(rel.inverse_relation), [])
            relations.append({'relationship_id': rel._id, 'target_id': src_obj._id})
            trg_obj.relationships[str(rel.inverse_relation)] = relations
            trg_obj.save()
            # TODO: Investigate using update API
            # trg_obj.update(**{f'relationships.{rel.inverse_relation}': relations})


def add_random_citations(objects, trg_obj: ObjectType, N=100):
    existing_citations = {c for _, c in trg_obj.relationships.isCitedBy}
    for _ in range(N):
        src_obj = random.choice(objects)
        while trg_obj._id == src_obj._id or src_obj._id in existing_citations:
            src_obj = random.choice(objects)
        existing_citations.add(src_obj._id)

        rel = _gen_relationship(src_obj, trg_obj, rel_type={'relation': 'cites', 'inverse_relation': 'isCitedBy'})
        rel.save()

        relations = getattr(src_obj.relationships, str(rel.relation), [])
        relations.append({'relationship_id': rel._id, 'target_id': trg_obj._id})
        src_obj.relationships[str(rel.relation)] = relations
        src_obj.save()
        relations = getattr(trg_obj.relationships, str(rel.inverse_relation), [])
        relations.append({'relationship_id': rel._id, 'target_id': src_obj._id})
        trg_obj.relationships[str(rel.inverse_relation)] = relations
        trg_obj.save()
