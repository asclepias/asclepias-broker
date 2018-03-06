from collections import defaultdict
from copy import deepcopy
from typing import List, Tuple
import sqlalchemy as sa

from .datastore import Group, GroupRelationship, GroupType, Identifier, \
    Relation
from .es import DB_RELATION_TO_ES, ObjectDoc, RelationshipDoc


# TODO: Move this to Group.identifiers
def _get_group_identifiers(id_group: Group) -> List[Identifier]:
    assert id_group.type == GroupType.Identity
    return [id2g.identifier for id2g in id_group.id2groups]


def _get_group_relationships(session, id_group: Group) -> List[GroupRelationship]:
    assert id_group.type == GroupType.Identity
    # NOTE: These GroupRelationships are mixed in terms of the source/taget
    # perspective.
    return session.query(GroupRelationship).filter(
        sa.or_(
            GroupRelationship.source_id == id_group.id,
            GroupRelationship.target_id == id_group.id),
        GroupRelationship.relation != Relation.IsIdenticalTo,
        GroupRelationship.type == GroupType.Identity,
    ).all()


def _build_object_relationships(id_group: Group, rels: List[GroupRelationship]):
    relationships = defaultdict(list)
    for r in rels:
        es_rel, es_inv_rel = DB_RELATION_TO_ES[r.relation]
        is_reverse = id_group.id == r.target_id
        rel_key = es_inv_rel if is_reverse else es_rel
        target_id = r.source_id if is_reverse else r.target_id
        relationships[rel_key].append({
            'RelationshipID': str(r.id),
            'TargetID': str(target_id),
        })
    return relationships


def index_identity_group(session,
                         id_group: Group,
                         ids: List[Identifier]=None,
                         rels: List[GroupRelationship]=None) -> ObjectDoc:
    ids = ids or _get_group_identifiers(id_group)
    rels = rels or _get_group_relationships(session, id_group)
    doc = deepcopy((id_group.data and id_group.data.json) or {})
    doc['Identifier'] = [{'ID': i.value, 'IDScheme': i.scheme} for i in ids]
    doc['Relationships'] = _build_object_relationships(id_group, rels)
    obj_doc = ObjectDoc(meta={'id': str(id_group.id)}, **doc)
    obj_doc.save()
    return obj_doc


def index_relationship_group(session, rel_group: GroupRelationship) -> RelationshipDoc:
    es_relation, es_inv_relation = DB_RELATION_TO_ES[rel_group.relation]
    doc = {
        'SourceID': str(rel_group.source_id),
        'TargetID': str(rel_group.target_id),
        'RelationshipType': {'Name': es_relation},
        'InverseRelation': es_inv_relation,
        'History': deepcopy((rel_group.data and rel_group.data.json) or {}),
    }

    rel_doc = RelationshipDoc(meta={'id': str(rel_group.id)}, **doc)
    rel_doc.save()
    return rel_doc
