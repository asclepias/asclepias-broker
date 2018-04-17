# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 CERN.
#
# Asclepias Broker is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
"""Elasticsearch indexing module."""

from collections import defaultdict
from copy import deepcopy
from itertools import chain
from typing import Iterable
from uuid import UUID

import sqlalchemy as sa

from .mappings.dsl import DB_RELATION_TO_ES, ObjectDoc, ObjectRelationshipsDoc
from .models import Group, GroupRelationship, GroupType, Identifier, Relation


# TODO: Move this to Group.identifiers
def _get_group_identifiers(id_group: Group) -> Iterable[Identifier]:
    assert id_group.type == GroupType.Identity
    return (id2g.identifier for id2g in id_group.id2groups)


def _get_group_relationships(group_id: UUID) -> Iterable[GroupRelationship]:
    # NOTE: These GroupRelationships are mixed in terms of the source/taget
    # perspective.
    return GroupRelationship.query.filter(
        sa.or_(
            GroupRelationship.source_id == group_id,
            GroupRelationship.target_id == group_id),
        GroupRelationship.relation != Relation.IsIdenticalTo,
        GroupRelationship.type == GroupType.Identity,
    )


def _build_object_relationships(group_id: UUID,
                                rels: Iterable[GroupRelationship]):
    # TODO: There's some issue here, depending on the perspective from which
    # the group id checks relationships (the reverse relationship...)
    relationships = defaultdict(list)
    for r in rels:
        es_rel, es_inv_rel = DB_RELATION_TO_ES[r.relation]
        is_reverse = str(group_id) == str(r.target_id)
        rel_key = es_inv_rel if is_reverse else es_rel
        target_id = r.source_id if is_reverse else r.target_id
        relationships[rel_key].append({
            'TargetID': str(target_id),
            'History': deepcopy((r.data and r.data.json) or {}),
        })
    return relationships


def delete_identity_group(id_group, with_relationships=True):
    """Delete an identity group and its relationships document indices."""
    obj_doc = ObjectDoc.get(str(id_group.id), ignore=404)
    if obj_doc:
        obj_doc.delete(ignore=404)

    obj_rel_doc = ObjectRelationshipsDoc.get(str(id_group.id), ignore=404)
    if obj_rel_doc:
        obj_rel_doc.delete(ignore=404)
    return obj_doc, obj_rel_doc


def index_identity_group(id_group: Group) -> ObjectDoc:
    """Index an identity group."""
    # Build source object identifiers
    doc = deepcopy((id_group.data and id_group.data.json) or {})

    ids = _get_group_identifiers(id_group)
    doc['Identifier'] = [{'ID': i.value, 'IDScheme': i.scheme} for i in ids]

    obj_doc = ObjectDoc(meta={'id': str(id_group.id)}, **doc)
    obj_doc.save()
    return obj_doc


def index_group_relationships(group_id: UUID) -> ObjectRelationshipsDoc:
    """Index the relationships of an identity group."""
    rels = _get_group_relationships(group_id)
    doc = _build_object_relationships(group_id, rels)
    rel_doc = ObjectRelationshipsDoc(meta={'id': str(group_id)}, **doc)
    rel_doc.save()
    return rel_doc


def update_indices(src_group: Group, trg_group: Group,
                   merged_group: Group=None):
    """Updates Elasticsearch indices with the updated groups."""
    # `src_group` and `trg_group` were merged into `merged_group`.
    if merged_group:
        # Delete Source and Traget groups
        delete_identity_group(src_group)
        delete_identity_group(trg_group)

        # Index the merged object and its relationships
        obj_doc = index_identity_group(merged_group)
        obj_rel_doc = index_group_relationships(merged_group.id)

        # Update all group relationships of the merged group
        # TODO: This can be optimized to avoid fetching a lot of the same
        # GroupMetadata, by keeping a temporary cache of them...
        relationships = chain.from_iterable(obj_rel_doc.to_dict().values())
        target_ids = [r.get('TargetID') for r in relationships]
        for i in target_ids:
            index_group_relationships(i)

        return (obj_doc, obj_rel_doc), (obj_doc, obj_rel_doc)

    # No groups were merged, this is a simple relationship

    # Index Source and Target objects and their relationships
    src_doc = index_identity_group(src_group)
    trg_doc = index_identity_group(trg_group)
    src_rel_doc = index_group_relationships(src_group.id)
    trg_rel_doc = index_group_relationships(trg_group.id)
    return (src_doc, src_rel_doc), (trg_doc, trg_rel_doc)
