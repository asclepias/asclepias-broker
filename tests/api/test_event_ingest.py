# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 CERN.
#
# Asclepias Broker is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Test citation queries."""
import json
import os

import requests
from copy import deepcopy
from flask import url_for

from asclepias_broker.jsonschemas import EVENT_SCHEMA


def test_simple_citations(live_server, data_dir, app):
    """Test simple citation queries."""
    with open(os.path.join(data_dir, 'payloads', 'events.json'), 'r') as fp:
        data = json.load(fp)
    event_url = url_for('asclepias_api.event', _external=True)
    resp = requests.post(event_url, json=data)
    assert resp.status_code == 202
    params = {
        'id': 'A',
        'scheme': 'doi',
        'relation': 'isCitedBy'
    }
    rels_url = url_for('asclepias_api.relationships', _external=True)
    resp = requests.get(rels_url, params=params)
    assert resp.status_code == 200
    d = resp.json()
    assert len(d['Source']['Identifier']) == 2
    assert len(d['Relationship']) == 3


def test_example_events(live_server, example_events, app, es):
    """Load the example events from asclepias_broker/examples."""
    event_url = url_for('asclepias_api.event', _external=True)
    for data in example_events:
        resp = requests.post(event_url, json=data)
        assert resp.status_code == 202


def test_invalid_payload(live_server, app, es):
    """Test error handling for ingestion."""
    event_url = url_for('asclepias_api.event', _external=True)
    # Completely invalid JSON structure
    data = {'invalid': 'true'}
    resp = requests.post(event_url, json=data)
    assert resp.status_code == 422
    data = {
        "ID": "41bcdb2c-9fb4-4948-a2ca-434493dc83b3",
        "EventType": "RelationshipCreated",
        "Time": "2018-01-01T08:00:00Z",
        "Creator": "ACME Inc.",
        "Source": "Test",
        "Payload": [
            {
                "Source": {
                    "Identifier": {
                        "ID": "10.1234/foobar.1234",
                        "IDScheme": "doi"
                    },
                    "Type": {
                        "Name": "unknown"
                    }
                },
                "RelationshipType": {
                    "Name": "IsRelatedTo",
                    "SubType": "IsIdenticalTo",
                    "SubTypeSchema": "DataCite"
                },
                "Target": {
                    "Identifier": {
                        "ID": "https://example.com/record/12345",
                        "IDScheme": "url"
                    },
                    "Type": {
                        "Name": "unknown"
                    }
                },
                "LinkPublicationDate": "2018-01-01",
                "LinkProvider": [
                    {
                        "Name": "Link Provider Ltd."
                    }
                ]
            }
        ]
    }
    # Make a copy of valid event payload for modification
    data_valid = deepcopy(data)
    # At least one payload is required
    data['Payload'] = []
    resp = requests.post(event_url, json=data)
    assert resp.status_code == 422
    assert 'is too short' in resp.text

    data = deepcopy(data_valid)
    # Fetch the maxItems constraint from schema
    maxitems = int(EVENT_SCHEMA['properties']['Payload']['maxItems'])
    # Go over maximum limit of payloads per request
    data['Payload'] = data_valid['Payload'] * (maxitems + 1)
    resp = requests.post(event_url, json=data)
    assert resp.status_code == 422
    assert 'is too long' in resp.text

    data = deepcopy(data_valid)
    # Unknown event type
    data['EventType'] = 'UnknownEventType'
    resp = requests.post(event_url, json=data)
    assert resp.status_code == 422
    assert resp.json()['message'].startswith(
        "'UnknownEventType' is not one of")

    data = deepcopy(data_valid)
    # Not matching identifier scheme
    data['Payload'][0]['Source']['Identifier']['IDScheme'] = 'unknown'
    resp = requests.post(event_url, json=data)
    assert resp.status_code == 422
    assert resp.json()['message'].startswith(
        "Validation error") and 'Invalid scheme' in resp.json()['message']

    data = deepcopy(data_valid)
    data['Time'] = 'abc'
    resp = requests.post(event_url, json=data)
    assert resp.status_code == 422
    assert "Invalid time format" in resp.json()['message']

