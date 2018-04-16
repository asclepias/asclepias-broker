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
from flask import url_for


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
        "Time": "1516728860",
        "Creator": "ACME Inc.",
        "Source": "Test",
        "Payload": []
    }
    # At least one payload is required
    resp = requests.post(event_url, json=data)
    assert resp.status_code == 422

    pl = {
        "Source": {
            "Identifier": {
                "ID": "A",
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
                "ID": "B",
                "IDScheme": "doi"
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
    data_big = dict(data)
    # Max limit of payloads per request is 200
    for i in range(201):
        data_big['Payload'].append(pl)
    resp = requests.post(event_url, json=data_big)
    assert resp.status_code == 422

