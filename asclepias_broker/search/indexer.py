# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 CERN.
#
# Asclepias Broker is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
"""Elasticsearch indexing module."""

import uuid
from copy import deepcopy
from itertools import chain
from typing import Dict, Iterable, Optional, Set, Tuple

import idutils
import sqlalchemy as sa
from elasticsearch.helpers import bulk as bulk_index
from elasticsearch_dsl import Q
from invenio_db import db
from invenio_search import current_search_client
from invenio_search.api import RecordsSearch
from sqlalchemy.orm import aliased

from ..core.models import Identifier, Relation
from ..graph.models import Group, GroupM2M, GroupRelationship, \
    GroupRelationshipM2M, GroupType
from ..utils import cached_func
from .utils import get_write_index


def build_id_info(id_: Identifier) -> dict:
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


@cached_func(
    prefix='asclepias.search.indexer.group_metadata',
    key_func=lambda f, group, *args, **kwargs: str(group.id))
def build_group_metadata(group: Group) -> dict:
    """Build the metadata for a group object."""
    if group.type == GroupType.Version:
        # Identifiers of the first identity group from all versions
        id_group = group.groups[0]

        # Remember visited parents in case of circular relations
        seen_ids = set()
        while True:
            if id_group.id in seen_ids:
                # Circular dependency. If parent seen, just pick current group
                break
            q = GroupRelationship.query.filter_by(
                target_id=id_group.id, relation=Relation.HasVersion)
            if not q.first():
                # If no longer possible to find parents, we are done
                break
            seen_ids.add(id_group.id)
            id_group = q.first().source
        ids = id_group.identifiers
        doc = deepcopy((id_group.data and id_group.data.json) or {})
        all_ids = sum([g.identifiers for g in group.groups], [])
    else:
        doc = deepcopy((group.data and group.data.json) or {})
        ids = group.identifiers
        all_ids = ids

    doc['Identifier'] = [build_id_info(i) for i in ids]
    doc['SearchIdentifier'] = [build_id_info(i) for i in all_ids]
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


def index_documents(docs: Iterable[dict], bulk: bool = False):
    """Index a list of documents into ES."""
    index_name = get_write_index()
    if bulk:
        bulk_index(
            client=current_search_client,
            actions=docs,
            index=index_name,
            doc_type='_doc',
            raise_on_error=False,
            chunk_size=300,  # TODO: Make configurable
            max_chunk_bytes=(30 * 1024 * 1024),  # TODO: Make configurable
        )
    else:
        for doc in docs:
            current_search_client.index(
                index=index_name, doc_type='doc', body=doc)


def build_doc(
    rel: GroupRelationship,
    src_grp: Group = None, trg_grp: Group = None,
    grouping: str = None
) -> dict:
    """Build the ES document for a relationship."""
    if not src_grp:
        if rel.type == GroupType.Identity:
            # Fetch the supergroup (Version) of the Identity relations
            src_grp = rel.source.supergroupsm2m[0].group
        else:
            src_grp = rel.source
    src_meta = build_group_metadata(src_grp)

    if not trg_grp:
        trg_grp = rel.target
    trg_meta = build_group_metadata(trg_grp)

    if rel.type == GroupType.Identity:
        rel_grp_int = rel.relation.value
        # TODO: This this is the correct value, but there's a bug
        # with superrelationshipsm2m being empty (shouldn't be the case)
        # rel_grp_int = rel.superrelationshipsm2m[0].relationship_id.int

    else:
        rel_grp_int = rel.id.int

    # We deterministically recompute the document ID based on
    # Source, Relationship and Target IDs
    doc_uuid = uuid.UUID(int=(src_grp.id.int ^ rel_grp_int ^ trg_grp.id.int))

    rel_meta = build_relationship_metadata(rel)
    grouping = grouping or \
        ('identity' if rel.type == GroupType.Identity else 'version')
    return {
        '_id': str(doc_uuid),
        '_source': {
            "ID": str(rel.id),
            "Grouping": grouping,
            "RelationshipType": rel.relation.name,
            "History": rel_meta,
            "Source": src_meta,
            "Target": trg_meta,
        },
    }


def index_identity_group_relationships(
    ig_id: str, vg_id: str,
    # TODO: Check if this parameter is actually used...
    exclude_group_ids: Optional[Tuple[str, str]] = None
):
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
        return build_doc(rel, src_grp=src_vg, trg_grp=ig_obj,
                         grouping='identity')

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
        return build_doc(rel, src_grp=vg_obj, trg_grp=trg_ig,
                         grouping='identity')

    outgoing_rel_docs = map(_build_doc, relationships)
    index_documents(chain(incoming_rel_docs, outgoing_rel_docs), bulk=True)


def index_version_group_relationships(group_id: str,
                                      exclude_group_id: str = None):
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
        return build_doc(rel, src_grp=rel.source, trg_grp=rel.target,
                         grouping='version')
    index_documents(map(_build_doc, relationships), bulk=True)


def delete_group_relations(group_ids: Iterable[str]):
    """Delete all relations for given group IDs from ES."""
    RecordsSearch(index='relationships').query('bool', should=[
            Q('terms', Source__ID=list(group_ids)),
            Q('terms', Target__ID=list(group_ids)),
    ]).params(conflicts='proceed').delete()  # ignore versioning conflicts


def update_indices(
    idx_ig: Set[str], del_ig: Set[str],
    idx_vg: Set[str], del_vg: Set[str],
    ig_to_vg_map: Dict[str, str]
):
    """Updates Elasticsearch indices with the updated groups."""
    # `src_group` and `trg_group` were merged into `merged_group`.
    delete_group_relations(del_ig | del_vg | idx_ig | idx_vg)
    for group_id in idx_vg:
        index_version_group_relationships(group_id)
    for group_id in idx_ig:
        index_identity_group_relationships(group_id, ig_to_vg_map[group_id])
