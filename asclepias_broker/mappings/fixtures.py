# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 CERN.
#
# Asclepias Broker is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
"""Fixtures and utilities for the Elasticsearch mappings."""

import random
import timeit
from contextlib import contextmanager
from datetime import datetime, timedelta
from uuid import uuid4

from faker import Faker

from ..api import RelationshipAPI
from .dsl import ObjectDoc, ObjectRelationshipsDoc


#
# Utils
#
@contextmanager
def progressbar(iterable, label, report_every, total_items):
    """Context manager to keep track of long iteration procedures progress."""
    print(label, report_every, total_items)
    start = datetime.now()
    print('{label} started at: {start}'.format(label=label, start=start))

    def _gen():
        for i, v in enumerate(iterable):
            if i % int(report_every) == 0:
                t = datetime.now()
                d = t - start
                rate = (int(i/d.total_seconds())
                        if d.total_seconds() != 0 else None)
                time_left = (timedelta(seconds=((total_items - i) / rate))
                             if rate else '???')
                rate_str = rate or "???"
                print(
                    '[{t}] - {i}..\t({d} - {rate} items/sec - ETA {time_left})'
                    .format(t=t, i=i, d=d, rate=rate_str, time_left=time_left))
            yield v
    yield _gen()
    end = datetime.now()
    print('{label} finished at: {end}, Total time: {total}'
          .format(label=label, end=end, total=(end-start)))


def benchmark_get_citations(N=100, **kwargs):
    """Run benchmarks for the citations query."""
    ids = [o._id for o in ObjectDoc.search().source(False).scan()]

    def _f():
        o = ObjectDoc.get(random.choice(ids))
        return len(RelationshipAPI.get_citations(
            random.choice([i.ID for i in o.Identifier])))
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
    ids = [{'ID': '{}{}'.format(faker.url(), base_value.hex),
            'IDScheme': 'url'}]
    if random.random() > 0.3:  # doi
        ids.append({'ID': '10.5072/{}'.format(base_value.hex),
                    'IDScheme': 'doi'})
    if random.random() > 0.8:  # second url
        ids.append({'ID': '{}{}'.format(faker.url(), base_value.hex),
                    'IDScheme': 'url'})
    if random.random() > 0.8:  # PMID
        ids.append({'ID': str(base_value.node), 'IDScheme': 'pmid'})
    return ids


def _gen_object(names, ids):
    return ObjectDoc(
        Title=faker.sentence(),
        Type=random.choice(OBJECT_TYPES),
        Identifier=ids,
        Creator=[random.choice(names) for _ in range(random.randint(1, 5))],
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
    """Seed Elasticsearch with mock data."""
    # delete_all()
    # create_all()

    names = [{'Name': n} for n in {faker.name() for _ in range(N)}]
    id_groups = [_gen_identifier() for _ in range(N)]
    object_ids = []

    with progressbar(id_groups, 'Objects...',
                     len(id_groups)/10, len(id_groups)) as progress:
        for ids in progress:
            obj = _gen_object(names, ids)
            obj.save()
            # Index an empty object relationships as well
            rel = ObjectRelationshipsDoc(meta={'id': obj._id})
            rel.save()
            object_ids.append(obj._id)

    with progressbar(range(N * 100), 'Relationships...',
                     N, N * 100) as progress:
        for _ in progress:
            src_obj_id = random.choice(object_ids)
            trg_obj_id = random.choice(object_ids)
            while trg_obj_id == src_obj_id:
                trg_obj_id = random.choice(object_ids)
            src_obj = ObjectDoc.get(src_obj_id)
            trg_obj = ObjectDoc.get(trg_obj_id)

            _gen_relationship(src_obj, trg_obj)


def add_random_citations(objects, trg_obj: ObjectDoc, N=100):
    """Add a random citations between two objects."""
    existing_citations = {c for _, c in trg_obj.Relationships.isCitedBy}
    for _ in range(N):
        src_obj = random.choice(objects)
        while trg_obj._id == src_obj._id or src_obj._id in existing_citations:
            src_obj = random.choice(objects)
        existing_citations.add(src_obj._id)
        rel = _gen_relationship(src_obj, trg_obj,
                                rel_type=RELATION_TYPES[0])  # citation type
        rel.save()

        relations = getattr(src_obj.Relationships,
                            str(rel.RelationshipType.Name), [])
        relations.append({'RelationshipID': rel._id, 'TargetID': trg_obj._id})
        src_obj.Relationships[str(rel.RelationshipType.Name)] = relations
        src_obj.save()
        relations = getattr(trg_obj.Relationships,
                            str(rel.InverseRelation), [])
        relations.append({'RelationshipID': rel._id, 'TargetID': src_obj._id})
        trg_obj.Relationships[str(rel.InverseRelation)] = relations
        trg_obj.save()
