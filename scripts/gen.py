#!/usr/bin/env python

import json
import os
import sys
import time
import uuid
from copy import deepcopy
from pathlib import Path

import jsonschema

# Path to Asclepias related JSONSchemas (../jsonschema)
schemas_path = Path(__file__).absolute().parent.parent / 'jsonschema'
with open(schemas_path / 'event.json', 'r') as fp:
    EVENT_SCHEMA = json.load(fp)
with open(schemas_path / 'scholix_v3_software.json', 'r') as fp:
    SCHOLIX_SCHEMA = json.load(fp)

EVENT_TYPE_MAP = {'C': 'relation_created', 'D': 'relation_deleted'}
SCHOLIX_RELATIONS = {'references', 'isReferencedBy', 'isSupplementTo',
                     'isSupplementedBy'}


INPUT_ITEMS_SCHEMA = {
    'definitions': {
        'Relation': {
            'type': 'array',
            'items': [
                {'type': 'string', 'title': 'Event type', 'enum': ['C', 'D']},
                {'type': 'string', 'title': 'Source identifier'},
                {'type': 'string', 'title': 'Relationship type',
                'enum': ['References', 'IsReferencedBy', 'IsSupplementTo',
                        'IsSupplementedBy', 'IsIdenticalTo', 'Cites',
                        'IsCitedBy']},
                {'type': 'string', 'title': 'Target identifier'},
                {'type': 'string', 'title': 'Publication Date'},
            ],
        },
    },
    'type': 'array',
    'items': {
        'oneOf': [
            # Allow nested, multi-payload events
            {'type': 'array', 'items': {'$ref': '#/definitions/Relation'}},
            {'$ref': '#/definitions/Relation'},
        ],
    }
}

TEST_INPUT = [
    [
        ['C', '10.1234/10', 'IsIdenticalTo', '10.1234/100', '2018-01-01'],
        ['C', '10.1234/20', 'References', '10.1234/10', '2018-01-01'],
    ],
    ['C', '10.1234/30', 'IsSupplementTo', '10.1234/10', '2018-01-01'],
    ['C', '10.1234/40', 'Cites', '10.1234/100', '2018-01-02'],
    ['C', '10.1234/20', 'Cites', '10.1234/10', '2018-01-03'],
    ['C', '10.1234/10', 'IsCitedBy', '10.1234/50', '2018-01-03'],
    ['C', '10.1234/10', 'IsCitedBy', '10.1234/40', '2018-01-04'],
]


class Event:

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
        self.time = getattr(self, 'time', str(int(time.time())))
        self.payloads = getattr(self, 'payloads', [])

    @classmethod
    def gen_identifier(cls, identifier, scheme=None, url=None):
        d = {'ID': identifier, 'IDScheme': scheme or 'DOI'}
        if url:
            d['IDURL'] = url
        return d

    @classmethod
    def gen_relationship_type(cls, relationship_type):
        if relationship_type not in SCHOLIX_RELATIONS:
            return {'Name': 'IsRelatedTo', 'SubType': relationship_type}
        return {'Name': relationship_type}

    @classmethod
    def gen_object(cls, source, type_=None, title=None, creator=None):
        return {
            'Identifier': cls.gen_identifier(source),
            'Type': type_ or {'Name': 'unknown'},
        }

    def set_event(self, type_=None, creator=None, source=None, time=None,
                  description=None, payloads=None, id_=None):
        self.event_type = type_ or getattr(self, 'event_type', 'relation_created')
        self.creator = creator or getattr(self, 'creator', 'Event Creator Inc.')
        self.source = source or getattr(self, 'source', 'Test')
        self.payloads = payloads or getattr(self, 'payloads', None)
        self.id = id_ or getattr(self, 'id', str(uuid.uuid4()))
        return self

    def add_payload(self, source, relation_type, target, publication_date,
                    provider=None):
        self.payloads.append({
            'Source': self.gen_object(source),
            'RelationshipType': self.gen_relationship_type(relation_type),
            'Target': self.gen_object(target),
            'LinkPublicationDate': publication_date,
            'LinkProvider': [provider or {'Name': 'Link Provider Ltd.'}]
        })
        return self

    @property
    def event(self):
        return {
            'id': self.id,
            'event_type': self.event_type,
            'time': self.time,
            'creator': self.creator,
            'source': self.source,
            'payload': self.payloads,
        }


def generate_payloads(infile):
    with open(infile, 'r') as fp:
        events = json.load(fp)
    jsonschema.validate(input_items, INPUT_ITEMS_SCHEMA)

    res = []
    for item in input_items:
        if isinstance(item[0], str):  # Single payload
            payloads = [item]
        else:  # Multiple payloads/relations
            payloads = item

        event_type = EVENT_TYPE_MAP[payloads[0][0]]
        evt = Event()
        evt.set_event(type_=event_type)
        for op, src, rel, trg, at in payloads:
            evt.add_payload(src, rel, trg, at)
        evt_data = evt.event
        jsonschema.validate(evt_data, EVENT_SCHEMA)
        res.append(evt_data)
    print(json.dumps(res, indent=2))


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python gen.py relations_input.json')
        exit(1)
    generate_payloads(sys.argv[1])
