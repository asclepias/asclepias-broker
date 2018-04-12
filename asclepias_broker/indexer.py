# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 CERN.
#
# Asclepias Broker is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

from collections import defaultdict
from copy import deepcopy
from typing import Iterable
from uuid import UUID
from invenio_db import db

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
    obj_doc = ObjectDoc.get(str(id_group.id), ignore=404)
    if obj_doc:
        obj_doc.delete(ignore=404)

    obj_rel_doc = ObjectRelationshipsDoc.get(str(id_group.id), ignore=404)
    if obj_rel_doc:
        obj_rel_doc.delete(ignore=404)
    return obj_doc, obj_rel_doc


def index_identity_group(id_group: Group) -> ObjectDoc:
    # Build source object identifiers
    doc = deepcopy((id_group.data and id_group.data.json) or {})

    ids = _get_group_identifiers(id_group)
    doc['Identifier'] = [{'ID': i.value, 'IDScheme': i.scheme} for i in ids]

    obj_doc = ObjectDoc(meta={'id': str(id_group.id)}, **doc)
    obj_doc.save()
    return obj_doc


def index_group_relationships(group_id: UUID) -> ObjectRelationshipsDoc:
    rels = _get_group_relationships(group_id)
    doc = _build_object_relationships(group_id, rels)
    rel_doc = ObjectRelationshipsDoc(meta={'id': str(group_id)}, **doc)
    rel_doc.save()
    return rel_doc
