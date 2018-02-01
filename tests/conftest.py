import json
import os
from pathlib import Path

import pytest

from asclepias_broker.broker import SoftwareBroker
from asclepias_broker.datastore import Base
from helpers import generate_payloads


@pytest.fixture(scope='function')
def broker(request):
    db_uri = os.environ.get('SQLALCHEMY_DATABASE_URI')
    broker = SoftwareBroker(db_uri)
    if request.param:
        for evt in generate_payloads(request.param):
            broker.handle_event(evt)
    yield broker

    # Drop all tables
    for tbl in reversed(Base.metadata.sorted_tables):
        broker.engine.execute(tbl.delete())


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
