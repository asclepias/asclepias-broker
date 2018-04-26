# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 CERN.
#
# Asclepias Broker is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Test event ingestion endpoints."""
import json
from copy import deepcopy

import pytest
from flask import url_for
from helpers import assert_es_equals_db
from invenio_oauth2server.models import Token

from asclepias_broker.jsonschemas import EVENT_SCHEMA


@pytest.fixture
def access_token(app, db):
    datastore = app.extensions['security'].datastore
    user = datastore.create_user(email='test@mail', password='', active=True)
    db.session.commit()
    token = Token.create_personal(
        't', user.id, scopes=[], is_internal=True).access_token
    db.session.commit()
    return token


@pytest.fixture
def auth_headers(access_token):
    return {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': 'Bearer {0}'.format(access_token),
    }


def test_endpoint_auth(client):
    """Load the example events from asclepias_broker/examples."""
    event_url = url_for('asclepias_api.event', _external=True)
    resp = client.post(event_url, content_type='application/json')
    assert resp.status_code == 401


def test_example_events(client, example_events, db, es_clear, auth_headers):
    """Load the example events from asclepias_broker/examples."""
    event_url = url_for('asclepias_api.event', _external=True)
    for data in example_events:
        resp = client.post(
            event_url, data=json.dumps(data), headers=auth_headers)
        assert resp.status_code == 202
    assert_es_equals_db()


def test_invalid_payload(client, db, es, auth_headers):
    """Test error handling for ingestion."""
    event_url = url_for('asclepias_api.event', _external=True)
    # Completely invalid JSON structure
    data = {'invalid': 'true'}
    resp = client.post(event_url, data=json.dumps(data), headers=auth_headers)
    assert resp.status_code == 422
    data_valid = [
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
    # At least one payload is required
    data = []
    resp = client.post(event_url, data=json.dumps(data), headers=auth_headers,
                       content_type='application/json')
    assert resp.status_code == 422
    assert 'is too short' in resp.json['message']

    data = deepcopy(data_valid)
    # Fetch the maxItems constraint from schema
    maxitems = int(EVENT_SCHEMA['maxItems'])

    # Go over maximum limit of payloads per request
    data = data * (maxitems + 1)
    resp = client.post(event_url, data=json.dumps(data), headers=auth_headers,
                       content_type='application/json')
    assert resp.status_code == 422
    assert 'is too long' in resp.json['message']

    # Not matching identifier scheme
    # TODO: For now we accept all IDSchemes
    data = deepcopy(data_valid)
    data[0]['Source']['Identifier']['IDScheme'] = 'unknown'
    resp = client.post(event_url, data=json.dumps(data), headers=auth_headers,
                       content_type='application/json')
    assert resp.status_code == 422
    assert resp.json['message'].startswith(
        "Validation error") and 'Invalid scheme' in resp.json['message']
