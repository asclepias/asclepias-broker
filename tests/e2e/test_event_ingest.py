"""Test citation queries."""
import pytest
import json
import os
import requests

from asclepias_broker.datastore import Identifier, GroupMetadata, GroupRelationshipMetadata
from collections import OrderedDict

from helpers import generate_payloads


def test_simple_citations(broker, data_dir):
    """Test simple citation queries."""
    with open(os.path.join(data_dir, 'payloads', 'events.json'), 'r') as fp:
        data = json.load(fp)
    resp = requests.post('http://localhost:5000/api/event', json=data)
    assert resp.status_code == 200
    params = {
        'id': 'A',
        'scheme': 'doi',
        'relation': 'isCitedBy'
    }
    resp = requests.get('http://localhost:5000/api/relationships', params=params)
    assert resp.status_code == 200
    d = resp.json()
    assert len(d['Source']['Identifier']) == 2
    assert len(d['Relationship']) == 3
