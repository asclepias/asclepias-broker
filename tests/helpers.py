import json
import sys
import time
import uuid

from typing import List, Tuple

from asclepias_broker.datastore import Relationship, Relation, Identifier,\
    Group, GroupType, GroupMetadata, Identifier2Group, GroupM2M,\
    GroupRelationship, GroupRelationshipM2M, Relationship2GroupRelationship, \
    GroupRelationshipMetadata
from asclepias_broker.tasks import get_or_create_groups
from asclepias_broker.jsonschemas import SCHOLIX_SCHEMA

import jsonschema

#
# Events generation helpers
#
EVENT_TYPE_MAP = {'C': 'RelationshipCreated', 'D': 'RelationshipDeleted'}
SCHOLIX_RELATIONS = {'References', 'IsReferencedBy', 'IsSupplementTo',
                     'IsSupplementedBy'}
RELATIONS_ENUM = [
    'References', 'IsReferencedBy', 'IsSupplementTo', 'IsSupplementedBy',
    'IsIdenticalTo', 'Cites', 'IsCitedBy', 'IsVersionOf', 'HasVersion']

INPUT_ITEMS_SCHEMA = {
    'definitions': {
        'Relationship': {
            'type': 'array',
            'items': [
                {'type': 'string', 'title': 'Event type', 'enum': ['C', 'D']},
                {'type': 'string', 'title': 'Source identifier'},
                {'type': 'string', 'title': 'Relation',
                 'enum': RELATIONS_ENUM},
                {'type': 'string', 'title': 'Target identifier'},
                {'type': 'string', 'title': 'Publication Date'},
            ],
        },
        'ObjMeta': {
            'type': 'object',
            'properties': {
                'Type': {
                    'type': 'string',
                    'enum': ['literature', 'dataset', 'unknown']
                },
                'Title': {
                    'type': 'string'
                },
                'Creator': {
                    'type': 'array',
                    'items': SCHOLIX_SCHEMA['definitions']['PersonOrOrgType']
                }
            }
        },
        'Metadata': {
            'type': 'object',
            'properties': {
                'Source': {
                    '$ref': '#definitions/ObjMeta'
                },
                'Target': {
                    '$ref': '#definitions/ObjMeta'
                },
                'LinkProvider': SCHOLIX_SCHEMA['definitions']['PersonOrOrgType']
            }
        }
    },
    'type': 'array',
    'items': {
        'oneOf': [
            # Allow nested, multi-payload events
            {'type': 'array', 'items': {'$ref': '#/definitions/Relationship'}},
            {'type': 'array', 'items': [
                    {'$ref': '#/definitions/Relationship'},
                    {'$ref': '#/definitions/Metadata'},
                ]
            },
            {'$ref': '#/definitions/Relationship'},
        ],
    }
}


class Event:
    """Event creation helper class."""

    def __init__(self, **kwargs):
        self.id = kwargs.get('id', str(uuid.uuid4()))
        self.time = kwargs.get('time', str(int(time.time())))
        self.payloads = kwargs.get('payload', [])
        self.event_type = kwargs.get('event_type', 'RelationshipCreated')
        self.creator = kwargs.get('creator', 'ACME Inc.')
        self.source = kwargs.get('source', 'Test')

    def _gen_identifier(self, identifier, scheme=None, url=None):
        d = {'ID': identifier, 'IDScheme': scheme or 'DOI'}
        if url:
            d['IDURL'] = url
        return d

    def _gen_object(self, source, metadata):
        type_ = metadata.get('Type')
        title = metadata.get('Title')
        creator = metadata.get('Creator')
        obj = {
            'Identifier': self._gen_identifier(source),
            'Type': type_ or {'Name': 'unknown'},
        }
        if title:
            obj['Title'] = title
        if creator:
            obj['Creator'] = creator
        return obj

    def _gen_relation(self, relation):
        if relation not in SCHOLIX_RELATIONS:
            return {'Name': 'IsRelatedTo', 'SubType': relation,
                    'SubTypeSchema': 'DataCite'}
        return {'Name': relation}

    def add_payload(self, source, relation, target, publication_date,
                    metadata=None):
        metadata = metadata or {}
        source_meta = metadata.get('Source', {})
        target_meta = metadata.get('Target', {})
        provider = metadata.get('LinkProvider')
        self.payloads.append({
            'Source': self._gen_object(source, source_meta),
            'RelationshipType': self._gen_relation(relation),
            'Target': self._gen_object(target, target_meta),
            'LinkPublicationDate': publication_date,
            'LinkProvider': [provider or {'Name': 'Link Provider Ltd.'}]
        })
        return self

    @property
    def event(self):
        return {
            'ID': self.id,
            'EventType': self.event_type,
            'Time': self.time,
            'Creator': self.creator,
            'Source': self.source,
            'Payload': self.payloads,
        }


def generate_payloads(input_items, event_schema=None):
    jsonschema.validate(input_items, INPUT_ITEMS_SCHEMA)
    events = []
    for item in input_items:

        if len(item) == 2 and isinstance(item[1], dict):  # Relation + Metadata
            evt = Event(event_type=EVENT_TYPE_MAP[item[0][0]])
            payload, metadata = item
            op, src, rel, trg, at = payload
            evt.add_payload(src, rel, trg, at, metadata)
            events.append(evt.event)
        else:
            if isinstance(item[0], str):  # Single payload
                payloads = [item]
            else:
                payloads = item
            evt = Event(event_type=EVENT_TYPE_MAP[payloads[0][0]])

            for op, src, rel, trg, at in payloads:
                evt.add_payload(src, rel, trg, at)
            events.append(evt.event)
    if event_schema:
        jsonschema.validate(events, {'type': 'array', 'items': event_schema})
    return events


def create_objects_from_relations(session, relationships: List[Tuple],
        metadata: List[Tuple[dict]]=None):
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
    identifiers = sorted(set(sum([[a,b] for a, _, b in relationships],[])))
    groups = []  # Cointains pairs of (Identifier2Group, Group2Group)
    for i in identifiers:
        id_ = Identifier(value=i, scheme='doi')
        session.add(id_)
        groups.append(get_or_create_groups(session, id_))
    rel_obj = []
    id_gr_relationships = []
    ver_gr_relationships = []
    for (src, rel, tar), (src_m, rel_m, tar_m) in zip(relationships, metadata):
        src_, tar_ = Identifier.get(session, src, 'doi'), \
            Identifier.get(session, tar, 'doi')
        r = Relationship(source=src_, target=tar_, relation=rel)
        session.add(r)
        rel_obj.append(r)
        s_id_gr, s_ver_gr = groups[identifiers.index(src)]
        t_id_gr, t_ver_gr = groups[identifiers.index(tar)]
        id_gr_rel = GroupRelationship(source=s_id_gr,
            target=t_id_gr, relation=rel, type=GroupType.Identity,
            id=uuid.uuid4())
        s_id_gr.data.update(src_m, validate=False)
        t_id_gr.data.update(tar_m, validate=False)

        grm = GroupRelationshipMetadata(group_relationship_id=id_gr_rel.id)
        session.add(grm)
        grm.update(rel_m, validate=False)
        session.add(Relationship2GroupRelationship(relationship=r,
            group_relationship=id_gr_rel))
        session.add(id_gr_rel)
        ver_gr_rel = GroupRelationship(source=s_ver_gr,
            target=t_ver_gr, relation=rel, type=GroupType.Version)
        session.add(GroupRelationshipM2M(relationship=ver_gr_rel,
                                         subrelationship=id_gr_rel))
        session.add(ver_gr_rel)
    session.commit()


def assert_grouping(session, grouping):
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

    id_groups = [g for g, t in zip(groups, group_types) if t == GroupType.Identity]
    uniqe_ids = set(sum(id_groups, []))

    # id_map is a mapping of str -> Identifier
    # E.g.: 'A' -> Instance('A', 'doi')
    id_map = dict(map(lambda x: (x, Identifier.get(session, x, 'doi')), uniqe_ids))

    group_map = []
    for g in groups:
        if isinstance(g[0], str):  # Identity group
            group_map.append(
                session.query(Identifier2Group).filter_by(
                    identifier=id_map[g[0]]).one().group)
        elif isinstance(g[0], int):  # GroupM2M
            group_map.append(
                session.query(GroupM2M).filter_by(
                    subgroup=group_map[g[0]]).one().group)

    rel_map = []
    for r in relationships:
        obj_a, relation, obj_b = r
        if isinstance(obj_a, str) and isinstance(obj_b, str):  # Identifiers relation
            rel_map.append(
                session.query(Relationship).filter_by(
                    source=id_map[obj_a], target=id_map[obj_b],
                    relation=relation).one()
            )
        elif isinstance(obj_a, int) and isinstance(obj_b, int):  # Groups relation
            rel_map.append(
                session.query(GroupRelationship).filter_by(
                    source=group_map[obj_a], target=group_map[obj_b],
                    relation=relation).one()
            )

    # Make sure all loaded identifiers are unique
    assert len(set(map(lambda x: x[1].id, id_map.items()))) == len(id_map)
    assert session.query(Identifier).count() == len(id_map)

    # Make sure there's correct number of Identitfier2Group records
    # and 'Identity'-type groups
    assert session.query(Identifier2Group).count() == len(id_map)
    assert session.query(Group).filter_by(
        type=GroupType.Identity).count() == len(id_groups)

    assert session.query(GroupMetadata).count() == len(id_groups)

    # Make sure that all loaded groups are unique
    assert len(set(map(lambda x: x.id, group_map))) == len(group_map)
    assert session.query(Group).count() == len(group_map)

    # Make sure there's correct number of GroupM2M records
    # and 'Version'-type groups
    m2m_groups = [g for g in groups if isinstance(g[0], int)]
    assert session.query(Group).filter_by(
        type=GroupType.Version).count() == len(m2m_groups)
    # There are as many M2M groups as there are Identity groups
    assert session.query(GroupM2M).count() == len(id_groups)

    # Make sure that all loaded relationships are unique
    id_rels = [r for r, t in zip(rel_map, relationship_types)
               if t is None]
    assert len(set(map(lambda x: x.id, id_rels))) == len(id_rels)
    assert session.query(Relationship).count() == len(id_rels)

    grp_rels = [r for r, t in zip(rel_map, relationship_types)
               if t is not None]
    # Make sure that all loaded groups relationships are unique
    assert len(set(map(lambda x: x.id, grp_rels))) == len(grp_rels)
    assert session.query(GroupRelationship).count() == len(grp_rels)

    # Make sure that GroupRelationshipM2M are correct
    id_grp_rels = [r for r, t in zip(rel_map, relationship_types)
                   if t == GroupType.Identity]
    # There are as many GroupRelationshipM2M objects as Identity Groups
    assert session.query(GroupRelationshipM2M).count() == len(id_grp_rels)

    # Same number of GroupRelationshipMetadata as GRelationships of type ID
    assert session.query(GroupRelationshipMetadata).count() == len(id_grp_rels)

    # There are as many Relationship to GR items as Relationships
    n_rel2grrels = sum([len(x[1]) for x in relationship_groups
                        if isinstance(rel_map[x[1][0]], Relationship)])
    assert session.query(Relationship2GroupRelationship).count() == n_rel2grrels

    # Make sure that all GroupRelationshipM2M are matching
    for group_rel, group_subrels in relationship_groups:
        for group_subrel in group_subrels:
            if isinstance(rel_map[group_subrel], Relationship):
                assert session.query(Relationship2GroupRelationship).filter_by(
                    relationship=rel_map[group_subrel],
                    group_relationship=rel_map[group_rel]).one()
            else:  # isinstance(rel_map[group_rel], GroupRelationship):
                assert session.query(GroupRelationshipM2M).filter_by(
                    relationship=rel_map[group_rel],
                    subrelationship=rel_map[group_subrel]).one()

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python gen.py relations_input.json')
        exit(1)
    with open(sys.argv[1], 'r') as fp:
        input_items = json.load(fp)
    res = generate_payloads(input_items)
    print(json.dumps(res, indent=2))
