"""Test ElasticSearch indexing."""

from typing import List, Tuple

import arrow
from helpers import create_objects_from_relations

from asclepias_broker.datastore import Group, GroupMetadata, Identifier, \
    Relation, Relationship, GroupType, GroupRelationship, GroupRelationshipMetadata
from asclepias_broker.es import ObjectDoc, RelationshipDoc
from asclepias_broker.indexer import index_identity_group
from asclepias_broker.tasks import get_or_create_groups, \
    merge_identity_groups, update_groups, update_metadata, update_indices


def dates_equal(a, b):
    return arrow.get(a) == arrow.get(b)


def _create_identity_groups(session, identifier_groups) -> List[Tuple[Group, GroupMetadata]]:
    all_groups = []
    for ids, metadata in identifier_groups:
        temp_ids = []
        temp_groups = []
        for i in ids:
            id_ = Identifier(value=i, scheme='doi')
            session.add(id_)
            temp_ids.append(id_)
            temp_groups.append(get_or_create_groups(session, id_)[0])
        base_id = temp_ids.pop()
        id_group, _ = get_or_create_groups(session, base_id)
        while len(temp_groups) > 0:
            merge_identity_groups(session, id_group, temp_groups.pop())
            session.commit()
            id_group, _ = get_or_create_groups(session, base_id)

        group_metadata = id_group.data or GroupMetadata(group=id_group)
        group_metadata.update(metadata)
        session.commit()
        all_groups.append((id_group, group_metadata))
    return all_groups


def _create_group_rel(session, src_identifier, trg_identifier, relation=None,
        metadata=None):
    relation = relation or Relation.Cites
    metadata = metadata or {'LinkProvider': [{'Name': 'Test provider'}],
                            'LinkPublicationDate': '2018-01-01'}
    src_id = Identifier.get(session, src_identifier, 'doi')
    trg_id = Identifier.get(session, trg_identifier, 'doi')
    rel = Relationship(source=src_id, target=trg_id, relation=relation)
    session.add(rel)
    session.commit()
    update_groups(session, rel)
    src_group, _ = get_or_create_groups(session, src_id)
    trg_group, _ = get_or_create_groups(session, trg_id)
    rel_group = session.query(GroupRelationship).filter_by(
        source=src_group, target=trg_group, relation=rel.relation,
        type=GroupType.Identity).one_or_none()
    rel_metadata = rel_group.data or \
        GroupRelationshipMetadata(group_relationship_id=rel_group.id)
    rel_metadata.update(metadata)
    session.commit()
    return src_group, trg_group, rel_group


def _gen_metadata(id_):
    return {
        'Title': 'Title for {}'.format(id_),
        'Creator': [{'Name': 'Creator for {}'.format(id_)}],
        'Type': {'Name': 'literature'},
        'PublicationDate': '2018-01-01',
    }


def test_init(es):
    assert es.indices.exists(index='objects')
    assert es.indices.exists(index='relationships')


def test_simple_groups(broker, es):
    s = broker.session

    ids = {'A': ('A1', 'A2', 'A3'), 'B': ('B1', 'B2'), 'C': ('C1',)}
    (group, group_metadata), = _create_identity_groups(s, [
        (ids['A'], _gen_metadata('A')),
    ])

    assert len(ObjectDoc.all()) == 0

    index_identity_group(s, group)
    es.indices.refresh()
    all_obj_docs = ObjectDoc.all()
    assert len(all_obj_docs) == 1

    obj_doc = all_obj_docs[0]
    assert obj_doc._id == str(group.id)
    assert obj_doc.Title == group_metadata.json['Title']
    assert obj_doc.Creator == group_metadata.json['Creator']
    assert dates_equal(obj_doc.PublicationDate, group_metadata.json['PublicationDate'])
    assert obj_doc.Identifier == [{'ID': i, 'IDScheme': 'doi'} for i in ids['A']]
    assert obj_doc.Relationships == {}

    groups = _create_identity_groups(s, [
        (ids['B'], _gen_metadata('B')),
        (ids['C'], _gen_metadata('C')),
    ])

    assert len(ObjectDoc.all()) == 1

    for group, _ in groups:
        index_identity_group(s, group)
    es.indices.refresh()
    assert len(ObjectDoc.all()) == 3


def test_simple_relationships(broker, es):
    s = broker.session

    ids = {'A': ('A1', 'A2', 'A3'), 'B': ('B1', 'B2'), 'C': ('C1',)}
    groups = _create_identity_groups(s, [
        (ids['A'], _gen_metadata('A')),
        (ids['B'], _gen_metadata('B')),
        (ids['C'], _gen_metadata('C')),
    ])

    for group, _ in groups:
        index_identity_group(s, group)
    es.indices.refresh()
    all_obj_docs = ObjectDoc.all()
    all_rel_docs = RelationshipDoc.all()
    assert len(all_obj_docs) == 3
    assert len(all_rel_docs) == 0

    src_group, trg_group, rel_group = _create_group_rel(s, 'A1', 'B1')
    update_indices(s, src_group, trg_group, rel_group)
    es.indices.refresh()

    all_obj_docs = ObjectDoc.all()
    all_rel_docs = RelationshipDoc.all()
    assert len(all_obj_docs) == 3
    assert len(all_rel_docs) == 1

    src_doc = ObjectDoc.get(str(src_group.id))
    assert len(src_doc.Relationships.cites) == 1
    assert src_doc.Relationships.cites[0] == {'RelationshipID': str(rel_group.id),
                                              'TargetID': str(trg_group.id)}

    trg_doc = ObjectDoc.get(str(trg_group.id))
    assert len(trg_doc.Relationships.isCitedBy) == 1
    assert trg_doc.Relationships.isCitedBy[0] == {'RelationshipID': str(rel_group.id),
                                                  'TargetID': str(src_group.id)}

    rel_doc = RelationshipDoc.get(str(rel_group.id))
    assert rel_doc.RelationshipType.Name == 'cites'
    assert rel_doc.InverseRelation == 'isCitedBy'
    assert rel_doc.SourceID == str(src_group.id)
    assert rel_doc.TargetID == str(trg_group.id)
    assert len(rel_doc.History) == 1
    assert rel_doc.History[0].LinkProvider == [{'Name': 'Test provider'}]
    assert dates_equal(rel_doc.History[0].LinkPublicationDate, '2018-01-01')
