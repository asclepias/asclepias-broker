# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 CERN.
#
# Asclepias Broker is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
"""Elasticsearch indexing module."""

from copy import deepcopy
from itertools import chain

import idutils
import sqlalchemy as sa
from elasticsearch.helpers import bulk as bulk_index
from elasticsearch_dsl import Q
from invenio_db import db
from invenio_search import current_search_client
from invenio_search.api import RecordsSearch
from sqlalchemy.orm import aliased

from .models import Group, GroupM2M, GroupRelationship, GroupRelationshipM2M, \
    GroupType


def build_id_info(id_):
    """Build information for the Identifier."""
    data = {
        'ID': id_.value,
        'IDScheme': id_.scheme
    }
    try:
        id_url = idutils.to_url(id_.value, id_.scheme)
        if id_url:
            data['IDURL'] = id_url
    except Exception:
        pass
    return data


def build_group_metadata(group: Group) -> dict:
    """Build the metadata for a group object."""
    if group.type == GroupType.Version:
        # Identifiers of the first identity group from all versions
        id_group = group.groups[0]
        ids = id_group.identifiers
        doc = deepcopy((id_group.data and id_group.data.json) or {})
    else:
        doc = deepcopy((group.data and group.data.json) or {})
        ids = group.identifiers

    doc['Identifier'] = [build_id_info(i) for i in ids]
    doc['ID'] = str(group.id)
    return doc


def build_relationship_metadata(rel: GroupRelationship) -> dict:
    """Build the metadata for a relationship."""
    if rel.type == GroupType.Version:
        # History of the first group relationship from all versions
        # TODO: Maybe concatenate all histories?
        id_rel = rel.relationships[0]
        return deepcopy((id_rel.data and id_rel.data.json) or {})
    else:
        return deepcopy((rel.data and rel.data.json) or {})


def index_documents(docs, bulk=False):
    """Index a list of documents into ES."""
    if bulk:
        bulk_index(
            client=current_search_client,
            actions=docs,
            index='relationships',
            doc_type='doc',
        )
    else:
        for doc in docs:
            current_search_client.index(
                index='relationships', doc_type='doc', body=doc)


def index_identity_group_relationships(ig_id: str, vg_id: str,
                                       exclude_group_ids: tuple=None):
    """Build the relationship docs for Identity relations."""
    # Build the documents for incoming Version2Identity relations

    ver_grp_cls = aliased(Group, name='ver_grp_cls')
    id_grp_cls = aliased(Group, name='id_grp_cls')
    exclude_ig_id, exclude_vg_id = (exclude_group_ids or (None, None))

    filter_cond = [
        ver_grp_cls.type == GroupType.Version,
        GroupRelationship.type == GroupType.Identity,
        GroupRelationship.target_id == ig_id,
    ]
    if exclude_ig_id:
        filter_cond.append(GroupRelationship.source_id != exclude_ig_id)

    relationships = (
        db.session.query(GroupM2M, GroupRelationship, ver_grp_cls)
        .join(id_grp_cls, GroupM2M.subgroup_id == id_grp_cls.id)
        .join(ver_grp_cls, GroupM2M.group_id == ver_grp_cls.id)
        .join(GroupRelationship, GroupRelationship.source_id == id_grp_cls.id)
        .filter(*filter_cond)
    )

    ig_obj = Group.query.get(ig_id)

    def _build_doc(row):
        _, rel, src_vg = row
        src_meta = build_group_metadata(src_vg)
        trg_meta = build_group_metadata(ig_obj)
        rel_meta = build_relationship_metadata(rel)
        return {
            "ID": str(rel.id),
            "Grouping": "identity",
            "RelationshipType": rel.relation.name,
            "History": rel_meta,
            "Source": src_meta,
            "Target": trg_meta,
        }

    incoming_rel_docs = map(_build_doc, relationships)

    # Build the documents for outgoing Version2Identity relations
    ver_grprel_cls = aliased(GroupRelationship, name='ver_grprel_cls')
    id_grprel_cls = aliased(GroupRelationship, name='id_grprel_cls')
    filter_cond = [
        Group.type == GroupType.Identity,
        ver_grprel_cls.type == GroupType.Version,
        id_grprel_cls.type == GroupType.Identity,
    ]
    if exclude_vg_id:
        filter_cond.append(ver_grprel_cls.target_id != exclude_vg_id)
    relationships = (
        db.session.query(id_grprel_cls, Group)
        .join(ver_grprel_cls, ver_grprel_cls.source_id == vg_id)
        .join(GroupRelationshipM2M, sa.and_(
            GroupRelationshipM2M.relationship_id == ver_grprel_cls.id,
            GroupRelationshipM2M.subrelationship_id == id_grprel_cls.id))
        .join(Group, id_grprel_cls.target_id == Group.id)
        .filter(*filter_cond)
    )

    vg_obj = Group.query.get(vg_id)

    def _build_doc(row):
        rel, trg_ig = row
        src_meta = build_group_metadata(vg_obj)
        trg_meta = build_group_metadata(trg_ig)
        rel_meta = build_relationship_metadata(rel)
        return {
            "ID": str(rel.id),
            "Grouping": "identity",
            "RelationshipType": rel.relation.name,
            "History": rel_meta,
            "Source": src_meta,
            "Target": trg_meta,
        }

    outgoing_rel_docs = map(_build_doc, relationships)
    index_documents(chain(incoming_rel_docs, outgoing_rel_docs), bulk=True)


def index_version_group_relationships(group_id: str,
                                      exclude_group_id: str=None):
    """Build the relationship docs for Version relations."""
    if exclude_group_id:
        filter_cond = sa.or_(
            sa.and_(GroupRelationship.source_id == group_id,
                    GroupRelationship.target_id != exclude_group_id),
            sa.and_(GroupRelationship.target_id == group_id,
                    GroupRelationship.source_id != exclude_group_id))
    else:
        filter_cond = sa.or_(
            GroupRelationship.source_id == group_id,
            GroupRelationship.target_id == group_id)

    relationships = GroupRelationship.query.filter(
        GroupRelationship.type == GroupType.Version,
        filter_cond
    )

    def _build_doc(rel):
        src_meta = build_group_metadata(rel.source)
        trg_meta = build_group_metadata(rel.target)
        rel_meta = build_relationship_metadata(rel)
        return {
            "ID": str(rel.id),
            "Grouping": "version",
            "RelationshipType": rel.relation.name,
            "History": rel_meta,
            "Source": src_meta,
            "Target": trg_meta,
        }
    index_documents(map(_build_doc, relationships), bulk=True)


def delete_group_relations(group_id):
    """Delete all relations for given group ID from ES."""
    RecordsSearch(index='relationships').query('bool', should=[
            Q('term', Source__ID=group_id),
            Q('term', Target__ID=group_id),
    ]).params(conflicts='proceed').delete()  # ignore versioning conflicts


def update_indices(src_ig, trg_ig, mrg_ig, src_vg, trg_vg, mrg_vg):
    """Updates Elasticsearch indices with the updated groups."""
    # `src_group` and `trg_group` were merged into `merged_group`.
    for grp_id in [src_ig, trg_ig, src_vg, trg_vg]:
        delete_group_relations(grp_id)

    if mrg_vg:
        index_version_group_relationships(mrg_vg)
    else:
        index_version_group_relationships(src_vg)
        index_version_group_relationships(trg_vg, exclude_group_id=src_vg)

    if mrg_ig:
        index_identity_group_relationships(mrg_ig, mrg_vg)
    else:
        index_identity_group_relationships(src_ig, src_vg)
        index_identity_group_relationships(trg_ig, trg_vg,
                                           exclude_group_ids=(src_ig, src_vg))
