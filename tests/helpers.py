import json
import sys
import time
import uuid

import jsonschema

#
# Events generation helpers
#
EVENT_TYPE_MAP = {'C': 'relationship_created', 'D': 'relationship_deleted'}
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
    },
    'type': 'array',
    'items': {
        'oneOf': [
            # Allow nested, multi-payload events
            {'type': 'array', 'items': {'$ref': '#/definitions/Relationship'}},
            {'$ref': '#/definitions/Relationship'},
        ],
    }
}


class Event:
    """Event creation helper class."""

    def __init__(self, **kwargs):
        self.id = kwargs.get('id', str(uuid.uuid4()))
        self.time = kwargs.get('time', str(int(time.time())))
        self.payloads = kwargs.get('payloads', [])
        self.event_type = kwargs.get('event_type', 'relationship_created')
        self.creator = kwargs.get('creator', 'ACME Inc.')
        self.source = kwargs.get('source', 'Test')

    def _gen_identifier(self, identifier, scheme=None, url=None):
        d = {'ID': identifier, 'IDScheme': scheme or 'DOI'}
        if url:
            d['IDURL'] = url
        return d

    def _gen_object(self, source, type_=None, title=None, creator=None):
        return {
            'Identifier': self._gen_identifier(source),
            'Type': type_ or {'Name': 'unknown'},
        }

    def _gen_relation(self, relation):
        if relation not in SCHOLIX_RELATIONS:
            return {'Name': 'IsRelatedTo', 'SubType': relation,
                    'SubTypeSchema': 'DataCite'}
        return {'Name': relation}

    def add_payload(self, source, relation, target, publication_date,
                    provider=None):
        self.payloads.append({
            'Source': self._gen_object(source),
            'RelationshipType': self._gen_relation(relation),
            'Target': self._gen_object(target),
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


def generate_payloads(input_items, event_schema=None):
    jsonschema.validate(input_items, INPUT_ITEMS_SCHEMA)
    events = []
    for item in input_items:
        if isinstance(item[0], str):  # Single payload
            payloads = [item]
        else:  # Multiple payloads/relations
            payloads = item

        evt = Event(event_type=EVENT_TYPE_MAP[payloads[0][0]])
        for op, src, rel, trg, at in payloads:
            evt.add_payload(src, rel, trg, at)
        events.append(evt.event)
    if event_schema:
        jsonschema.validate(events, {'type': 'array', 'items': event_schema})
    return events


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python gen.py relations_input.json')
        exit(1)
    with open(sys.argv[1], 'r') as fp:
        input_items = json.load(fp)
    res = generate_payloads(input_items)
    print(json.dumps(res, indent=2))
