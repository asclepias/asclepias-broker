# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 CERN.
#
# Asclepias Broker is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
"""Test helpers."""

import uuid
from typing import List, Tuple

import jsonschema
from invenio_db import db
from invenio_search import RecordsSearch, current_search

from asclepias_broker.core.models import Identifier, Relationship
from asclepias_broker.graph.api import get_or_create_groups
from asclepias_broker.graph.models import Group, GroupM2M, GroupRelationship, \
    GroupRelationshipM2M, GroupType, Identifier2Group, \
    Relationship2GroupRelationship
from asclepias_broker.jsonschemas import SCHOLIX_RELATIONS
from asclepias_broker.metadata.models import GroupMetadata, \
    GroupRelationshipMetadata
from asclepias_broker.search import tasks as search_tasks

#
# Events generation helpers
#
DATACITE_RELATIONS = [
    'References', 'IsReferencedBy', 'IsSupplementTo', 'IsSupplementedBy',
    'IsIdenticalTo', 'Cites', 'IsCitedBy', 'IsVersionOf', 'HasVersion']


def gen_identifier(identifier, scheme, url=None):
    """Generate identifier dictionary."""
    d = {'ID': identifier, 'IDScheme': scheme}
    if url:
        d['IDURL'] = url
    return d


def gen_relation(relation):
    """Generate relation dictionary."""
    assert relation in DATACITE_RELATIONS
    if relation not in SCHOLIX_RELATIONS:
        return {'Name': 'IsRelatedTo', 'SubType': relation,
                'SubTypeSchema': 'DataCite'}
    return {'Name': relation}


def gen_object(identifier, metadata):
    """Generate a object dicitonary (source or target)."""
    title = metadata.get('Title')
    creator = metadata.get('Creator')
    obj = {
        'Identifier': gen_identifier(identifier, 'doi'),
        'Type': metadata.get('Type', {'Name': 'unknown'}),
    }
    if title:
        obj['Title'] = title
    if creator:
        obj['Creator'] = creator
    return obj


def generate_relationship(min_rel_tuple):
    """
    Generate full relationship object from minimal description.

    Generates full scholix relationship object from minimal relationship
    description provided as a triplet (source, relation, target).
    """
    def _gen_identifier(identifier, scheme=None, url=None):
        d = {'ID': identifier, 'IDScheme': scheme or 'DOI'}
        if url:
            d['IDURL'] = url
        return d

    def _gen_object(obj, metadata):
        title = metadata.get('Title')
        creator = metadata.get('Creator')
        obj = {
            'Identifier': _gen_identifier(obj),
            'Type': metadata.get('Type', {'Name': 'unknown'}),
        }
        if title:
            obj['Title'] = title
        if creator:
            obj['Creator'] = creator
        return obj

    def _gen_relation(relation):
        assert relation in DATACITE_RELATIONS
        if relation not in SCHOLIX_RELATIONS:
            return {'Name': 'IsRelatedTo', 'SubType': relation,
                    'SubTypeSchema': 'DataCite'}
        return {'Name': relation}
    if len(min_rel_tuple) == 3:
        source, relation, target = min_rel_tuple
        metadata = {}
    else:
        source, relation, target, metadata = min_rel_tuple

    return {
        'Source': _gen_object(source, metadata.get('Source', {})),
        'RelationshipType': _gen_relation(relation),
        'Target': _gen_object(target, metadata.get('Target', {})),
        'LinkPublicationDate': metadata.get('LinkPublicationDate',
                                            '2018-01-01'),
        'LinkProvider': [metadata.get('LinkProvider',
                                      {'Name': 'Link Provider Ltd.'})]
    }


def generate_payload(item, event_schema=None):
    """Generate event payload."""
    if isinstance(item[0], str):  # Single payload
        payload = [item]
    else:
        payload = item

    event = [generate_relationship(rel) for rel in payload]
    if event_schema:
        jsonschema.validate(event, event_schema)
    return event


def create_objects_from_relations(relationships: List[Tuple],
                                  metadata: List[Tuple[dict]] = None):
    """Given a list of relationships, create all corresponding DB objects.

    Optional 'metadata' list can be passed, which contains corresponding
    metadata items for each of the relationships, i.e., a triplet of Source,
    Relation and Target metadata.

    E.g.:
        relationships = [
            ('A', Relation.Cites, 'B'),
            ('C', Relation.Cites, 'D'),
        ]

        metadata = [
            ({<source-1>}, {<relation-1>}, {<target-1>}),
            ({<source-2>}, {<relation-2>}, {<target-2>}),
        ]

        Will create Identifier, Relationship, Group and all M2M objects.
    """
    if not metadata:
        metadata = [({}, {}, {}) for _ in range(len(relationships))]
    assert len(relationships) == len(metadata)
    identifiers = sorted(set(sum([[a, b] for a, _, b in relationships], [])))
    groups = []  # Contains pairs of (Identifier2Group, Group2Group)
    for i in identifiers:
        id_ = Identifier(value=i, scheme='doi')
        db.session.add(id_)
        groups.append(get_or_create_groups(id_))
    rel_obj = []
    for (src, rel, tar), (src_m, rel_m, tar_m) in zip(relationships, metadata):
        src_, tar_ = Identifier.get(src, 'doi'), \
            Identifier.get(tar, 'doi')
        r = Relationship(source=src_, target=tar_, relation=rel)
        db.session.add(r)
        rel_obj.append(r)
        s_id_gr, s_ver_gr = groups[identifiers.index(src)]
        t_id_gr, t_ver_gr = groups[identifiers.index(tar)]
        id_gr_rel = GroupRelationship(
            source=s_id_gr, target=t_id_gr, relation=rel,
            type=GroupType.Identity, id=uuid.uuid4())
        s_id_gr.data.update(src_m, validate=False)
        t_id_gr.data.update(tar_m, validate=False)

        grm = GroupRelationshipMetadata(group_relationship_id=id_gr_rel.id)
        db.session.add(grm)
        grm.update(rel_m, validate=False)
        db.session.add(Relationship2GroupRelationship(
            relationship=r, group_relationship=id_gr_rel))
        db.session.add(id_gr_rel)
        ver_gr_rel = GroupRelationship(
            source=s_ver_gr, target=t_ver_gr, relation=rel,
            type=GroupType.Version)
        db.session.add(GroupRelationshipM2M(
            relationship=ver_gr_rel, subrelationship=id_gr_rel))
        db.session.add(ver_gr_rel)
    db.session.commit()


def assert_grouping(grouping):
    """Determine if database state corresponds to 'grouping' definition.

    See tests in test_grouping.py for example input.
    """
    groups, relationships, relationship_groups = grouping
    group_types = [
        (GroupType.Identity if isinstance(g[0], str) else GroupType.Version)
        for g in groups]

    # Mapping 'relationship_types' is a mapping between relationship index to:
    # * None if its a regular Relation between Identifiers
    # * GroupType.Identity if it's a relation between 'Identity'-type Groups
    # * GroupType.Version if it's a relation between 'Version'-type Groups
    relationship_types = [None if isinstance(r[0], str) else group_types[r[0]]
                          for r in relationships]

    id_groups = [g for g, t in zip(groups, group_types)
                 if t == GroupType.Identity]
    uniqe_ids = set(sum(id_groups, []))

    # id_map is a mapping of str -> Identifier
    # E.g.: 'A' -> Instance('A', 'doi')
    id_map = dict(map(lambda x: (x, Identifier.get(x, 'doi')), uniqe_ids))

    group_map = []
    for g in groups:
        if isinstance(g[0], str):  # Identity group
            group_map.append(
                Identifier2Group.query.filter_by(
                    identifier=id_map[g[0]]).one().group)
        elif isinstance(g[0], int):  # GroupM2M
            group_map.append(
                GroupM2M.query.filter_by(
                    subgroup=group_map[g[0]]).one().group)

    rel_map = []
    for r in relationships:
        obj_a, relation, obj_b = r

        if isinstance(obj_a, str) and isinstance(obj_b, str):
            # Identifiers relation
            rel_map.append(
                Relationship.query.filter_by(
                    source=id_map[obj_a], target=id_map[obj_b],
                    relation=relation).one()
            )
        elif isinstance(obj_a, int) and isinstance(obj_b, int):
            # Groups relation
            rel_map.append(
                GroupRelationship.query.filter_by(
                    source=group_map[obj_a], target=group_map[obj_b],
                    relation=relation).one()
            )

    # Make sure all loaded identifiers are unique
    assert len(set(map(lambda x: x[1].id, id_map.items()))) == len(id_map)
    assert Identifier.query.count() == len(id_map)

    # Make sure there's correct number of Identitfier2Group records
    # and 'Identity'-type groups
    assert Identifier2Group.query.count() == len(id_map)
    assert Group.query.filter_by(
        type=GroupType.Identity).count() == len(id_groups)

    assert GroupMetadata.query.count() == len(id_groups)

    # Make sure that all loaded groups are unique
    assert len(set(map(lambda x: x.id, group_map))) == len(group_map)
    assert Group.query.count() == len(group_map)

    # Make sure there's correct number of GroupM2M records
    # and 'Version'-type groups
    m2m_groups = [g for g in groups if isinstance(g[0], int)]
    assert Group.query.filter_by(
        type=GroupType.Version).count() == len(m2m_groups)
    # There are as many M2M groups as there are Identity groups
    assert GroupM2M.query.count() == len(id_groups)

    # Make sure that all loaded relationships are unique
    id_rels = [r for r, t in zip(rel_map, relationship_types)
               if t is None]
    assert len(set(map(lambda x: x.id, id_rels))) == len(id_rels)
    assert Relationship.query.count() == len(id_rels)

    grp_rels = [r for r, t in zip(rel_map, relationship_types)
                if t is not None]
    # Make sure that all loaded groups relationships are unique
    assert len(set(map(lambda x: x.id, grp_rels))) == len(grp_rels)
    assert GroupRelationship.query.count() == len(grp_rels)

    # Make sure that GroupRelationshipM2M are correct
    id_grp_rels = [r for r, t in zip(rel_map, relationship_types)
                   if t == GroupType.Identity]
    # There are as many GroupRelationshipM2M objects as Identity Groups
    assert GroupRelationshipM2M.query.count() == len(id_grp_rels)

    # Same number of GroupRelationshipMetadata as GRelationships of type ID
    assert GroupRelationshipMetadata.query.count() == len(id_grp_rels)

    # There are as many Relationship to GR items as Relationships
    n_rel2grrels = sum([len(x[1]) for x in relationship_groups
                        if isinstance(rel_map[x[1][0]], Relationship)])
    assert Relationship2GroupRelationship.query.count() == n_rel2grrels

    # Make sure that all GroupRelationshipM2M are matching
    for group_rel, group_subrels in relationship_groups:
        for group_subrel in group_subrels:
            if isinstance(rel_map[group_subrel], Relationship):
                assert Relationship2GroupRelationship.query.filter_by(
                    relationship=rel_map[group_subrel],
                    group_relationship=rel_map[group_rel]).one()
            else:  # isinstance(rel_map[group_rel], GroupRelationship):
                assert GroupRelationshipM2M.query.filter_by(
                    relationship=rel_map[group_rel],
                    subrelationship=rel_map[group_subrel]).one()


def normalize_es_result(es_result):
    """Turn a single ES result (relationship doc) into a normalized format."""
    return (
        ('RelationshipType', es_result['RelationshipType']),
        ('Grouping', es_result['Grouping']),
        ('ID', es_result['ID']),
        ('SourceID', es_result['Source']['ID']),
        ('TargetID', es_result['Target']['ID']),
    )


def normalize_db_result(db_result):
    """Turn a single DB result (GroupRelationship) into a normalized format."""
    # For Identity GroupRelationships and for SourceID we fetch a
    # Version Group of the source
    if db_result.type == GroupType.Identity:
        source_id = db_result.source.supergroupsm2m[0].group.id
    else:
        source_id = db_result.source.id

    return (
        ('RelationshipType', db_result.relation.name),
        ('Grouping', db_result.type.name.lower()),
        ('ID', str(db_result.id)),
        ('SourceID', str(source_id)),
        ('TargetID', str(db_result.target.id)),
    )


def assert_es_equals_db():
    """Assert that the relationships in ES the GroupRelationships in DB.

    NOTE: This tests takes the state of the DB as the reference for comparison.
    """
    # Wait for ES to be available
    current_search.flush_and_refresh('relationships')

    # Fetch all DB objects and all ES objects
    es_q = list(RecordsSearch(index='relationships').query().scan())
    db_q = GroupRelationship.query.all()

    # normalize and compare two sets
    es_norm_q = list(map(normalize_es_result, es_q))
    db_norm_q = list(map(normalize_db_result, db_q))
    assert set(es_norm_q) == set(db_norm_q)


def reindex_all_relationships():
    """Eagerly reindexes all relationships."""
    search_tasks.reindex_all_relationships.s(
        destroy=True, split=False).apply()
    current_search.flush_and_refresh('relationships')
