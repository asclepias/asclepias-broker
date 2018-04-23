# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 CERN.
#
# Asclepias Broker is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Test search endpoint."""

from flask import url_for


def test_invalid_search_parameters(client):
    search_url = url_for('invenio_records_rest.relid_list')

    params = {}
    resp = client.get(search_url)
    assert resp.status_code == 400
    assert resp.json['message'] == 'Validation error.'
    assert resp.json['errors'][0]['field'] == 'id'

    params['id'] = 'some-id'
    resp = client.get(search_url, query_string=params)
    assert resp.status_code == 400
    assert resp.json['message'] == 'Validation error.'
    assert len(resp.json['errors']) == 1
    assert resp.json['errors'][0]['field'] == 'scheme'

    params['scheme'] = 'doi'
    resp = client.get(search_url, query_string=params)
    assert resp.status_code == 400
    assert resp.json['message'] == 'Validation error.'
    assert len(resp.json['errors']) == 1
    assert resp.json['errors'][0]['field'] == 'relation'

    params['relation'] = 'not-a-valid-value'
    resp = client.get(search_url, query_string=params)
    assert resp.status_code == 400
    assert resp.json['message'] == 'Validation error.'
    assert len(resp.json['errors']) == 1
    assert resp.json['errors'][0]['field'] == 'relation'

    params['relation'] = 'isCitedBy'
    resp = client.get(search_url, query_string=params)
    assert resp.status_code == 200
