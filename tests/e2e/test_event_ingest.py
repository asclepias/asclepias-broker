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


def test_simple_citations(live_server, data_dir):
    """Test simple citation queries."""
    with open(os.path.join(data_dir, 'payloads', 'events.json'), 'r') as fp:
        data = json.load(fp)
    resp = requests.post(url_for('asclepias_api.event_receiver', _external=True), json=data)
    assert resp.status_code == 200
    params = {
        'id': 'A',
        'scheme': 'doi',
        'relation': 'isCitedBy'
    }
    resp = requests.get(url_for('asclepias_api.api_relationships', _external=True), params=params)
    assert resp.status_code == 200
    d = resp.json()
    assert len(d['Source']['Identifier']) == 2
    assert len(d['Relationship']) == 3
