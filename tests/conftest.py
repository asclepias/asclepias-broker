import json
import os
from pathlib import Path

import pytest

from asclepias_broker.broker import SoftwareBroker
from asclepias_broker.es import create_all, delete_all, es_client
from asclepias_broker.datastore import Base
from helpers import generate_payloads

from sqlalchemy_utils.functions import create_database, database_exists, drop_database


@pytest.fixture()
def es():
    create_all()
    es_client.indices.refresh()
    yield es_client
    delete_all()


@pytest.fixture()
def broker(es):
    db_uri = os.environ.get('SQLALCHEMY_DATABASE_URI')
    broker_ = SoftwareBroker(db_uri)
    yield broker_

    # Close all open sessions sand drop all tables
    broker_.session.close_all()
    Base.metadata.drop_all(broker_.engine)


#
# JSON schema and test data loading fixtures
#
@pytest.fixture
def test_dir():
    return Path(__file__)


@pytest.fixture
def data_dir(test_dir):
    return test_dir / 'data'


@pytest.fixture
def base_dir(test_dir):
    return test_dir.parent


@pytest.fixture
def schema_dir(base_dir):
    return base_dir / 'asclepias_broker' / 'jsonschema'


@pytest.fixture
def event_schema(schema_dir):
    with open(schema_dir / 'event.json', 'r') as fp:
        return json.load(fp)
