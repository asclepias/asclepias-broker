# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 CERN.
#
# Asclepias Broker is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Test ElasticSearch indexing."""

from collections import defaultdict
from copy import deepcopy

import arrow
import sqlalchemy as sa
from helpers import create_objects_from_relations, generate_payloads
from invenio_search import current_search_client

from asclepias_broker.api import EventAPI
from asclepias_broker.api.ingestion import get_group_from_id
from asclepias_broker.indexer import update_indices
from asclepias_broker.mappings.dsl import DB_RELATION_TO_ES, ObjectDoc, \
    ObjectRelationshipsDoc
from asclepias_broker.models import GroupRelationship, GroupType, Relation


def _handle_events(evtsrc):
    events = generate_payloads(evtsrc)
    for ev in events:
        EventAPI.handle_event(ev)


def dates_equal(a, b):
    return arrow.get(a) == arrow.get(b)


def _group_data(id_):
    return {
        'Title': 'Title for {}'.format(id_),
        'Creator': [{'Name': 'Creator for {}'.format(id_)}],
        'Type': {'Name': 'literature'},
        'PublicationDate': '2018-01-01',
    }


def _rel_data():
    return {'LinkProvider': {'Name': 'Test provider'},
            'LinkPublicationDate': '2018-01-01'}


def _scholix_data(src_id, trg_id):
    return {
        'Source': _group_data(src_id),
        'Target': _group_data(trg_id),
        **_rel_data(),
    }


def _build_object_relationships(group_id):
    rels = GroupRelationship.query.filter(
        sa.or_(
            GroupRelationship.source_id == group_id,
            GroupRelationship.target_id == group_id),
        GroupRelationship.relation != Relation.IsIdenticalTo,
        GroupRelationship.type == GroupType.Identity,
    )
    relationships = defaultdict(list)
    for r in rels:
        es_rel, es_inv_rel = DB_RELATION_TO_ES[r.relation]
        is_reverse = group_id == r.target_id
        rel_key = es_inv_rel if is_reverse else es_rel
        target_id = r.source_id if is_reverse else r.target_id
        relationships[rel_key].append({
            'TargetID': str(target_id),
            'History': deepcopy((r.data and r.data.json) or {}),
        })
    return relationships


def _assert_equal_rels(model, doc):
    for rt in ('cites', 'isCitedBy', 'isSupplementTo', 'isSupplementedBy',
               'isRelatedTo'):
        model_rels = model.get(rt, [])
        es_rels = getattr(doc, rt, [])
        assert len(model_rels) == len(es_rels)
        model_rels_set = {
            (r['TargetID'],
             frozenset((h['LinkProvider']['Name'],
                        arrow.get(h['LinkPublicationDate']))
                       for h in r['History']))
            for r in model_rels
        }
        es_rels_set = {
            (r.TargetID,
             frozenset((h.LinkProvider.Name, arrow.get(h.LinkPublicationDate))
                       for h in r.History))
            for r in es_rels
        }
        assert model_rels_set == es_rels_set


def _assert_equal_doc_and_model(doc, rel_doc, model):
    db_data = model.data.json
    db_ids = [id2g.identifier.value for id2g in model.id2groups]
    db_rels = _build_object_relationships(model.id)

    assert doc._id == str(model.id)
    assert rel_doc._id == doc._id
    assert doc.Title == db_data['Title']
    assert doc.Creator == db_data['Creator']
    assert dates_equal(doc.PublicationDate, db_data['PublicationDate'])
    assert doc.Identifier == [{'ID': i, 'IDScheme': 'doi'} for i in db_ids]
    _assert_equal_rels(db_rels, rel_doc)


def test_simple_groups(db, es_clear):
    _handle_events([
        (['C', '10.100/zenodo.123', 'Cites', 'B', '2018-01-01'], _scholix_data('A', 'B')),
        #(['C', 'A1', 'Cites', 'B', '2018-01-01'], _scholix_data('A1', 'B')),
        #(['C', 'C', 'Cites', 'B', '2018-01-01'], _scholix_data('C', 'B')),
        # (['C', 'B', 'IsIdenticalTo', 'B1', '2018-01-01'],
        #  _scholix_data('B', 'B1')),
        #(['C', 'A1', 'IsIdenticalTo', 'A', '2018-01-01'],
        # _scholix_data('A1', 'A')),
    ])

    # metadata = [
    #     (_group_data('A'), _rel_data(), _group_data('B'))
    # ]

    # create_objects_from_relations(rels, metadata)

    # assert len(ObjectDoc.all()) == 0

    # src = get_group_from_id('A')
    # trg = get_group_from_id('B')
    # (src_doc, src_rel_doc), (trg_doc, trg_rel_doc) = update_indices(src, trg)
    # current_search_client.indices.refresh()

    # all_obj_docs = ObjectDoc.all()
    # all_obj_rel_docs = ObjectRelationshipsDoc.all()
    # assert len(all_obj_rel_docs) == len(all_obj_docs) == 2

    # _assert_equal_doc_and_model(src_doc, src_rel_doc, src)
    # _assert_equal_doc_and_model(trg_doc, trg_rel_doc, trg)


def test_simple_relationship(db, es_clear):

    rels = [
        ('A', Relation.Cites, 'B'),
    ]

    metadata = [
        (_group_data('A'), _rel_data(), _group_data('B'))
    ]

    create_objects_from_relations(rels, metadata)

    #assert len(ObjectDoc.all()) == 0

    src = get_group_from_id('A')
    trg = get_group_from_id('B')
    update_indices(src, trg)
    current_search_client.indices.refresh()

    all_obj_docs = ObjectDoc.all()
    all_obj_rel_docs = ObjectRelationshipsDoc.all()
    assert len(all_obj_rel_docs) == len(all_obj_docs) == 2

    _assert_equal_doc_and_model(src_doc, src_rel_doc, src)
    _assert_equal_doc_and_model(trg_doc, trg_rel_doc, trg)
