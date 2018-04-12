# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 CERN.
#
# Asclepias Broker is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

import json
import os

import pytest

from invenio_db import db

from asclepias_broker.app import create_app
from asclepias_broker.broker import SoftwareBroker
from asclepias_broker.models import Base
from asclepias_broker.es import create_all, delete_all, es_client


@pytest.fixture
def es():
    create_all()
    es_client.indices.refresh()
    yield es_client
    delete_all()


@pytest.fixture
def broker(es):
    db_uri = os.environ.get('SQLALCHEMY_DATABASE_URI')
    broker_ = SoftwareBroker(db_uri)
    yield broker_

    # Close all open sessions sand drop all tables
    broker_.session.close_all()
    Base.metadata.drop_all(broker_.engine)


@pytest.fixture
def app(es):
    app = create_app()
    yield app
    app.broker.session.close_all()
    Base.metadata.drop_all(app.broker.engine)


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
