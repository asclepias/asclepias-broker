# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 CERN.
#
# Asclepias Broker is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

import json
import os

import pytest

from invenio_app.factory import create_api
from invenio_db import db

from asclepias_broker.es import create_all, delete_all, es_client


@pytest.fixture
def es():
    create_all()
    es_client.indices.refresh()
    yield es_client
    delete_all()


@pytest.fixture(scope='module')
def create_app():
    return create_api


#
# JSON schema and test data loading fixtures
#
@pytest.fixture
def tests_dir():
    return os.path.dirname(__file__)


@pytest.fixture
def data_dir(tests_dir):
    return os.path.join(tests_dir, 'data')


@pytest.fixture
def base_dir(tests_dir):
    return os.path.dirname(tests_dir)


@pytest.fixture
def schema_dir(base_dir):
    return os.path.join(base_dir, 'asclepias_broker', 'jsonschema')


@pytest.fixture
def event_schema(schema_dir):
    with open(os.path.join(schema_dir, 'event.json'), 'r') as fp:
        return json.load(fp)
