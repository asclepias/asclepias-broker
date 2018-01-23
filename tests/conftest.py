import json
from pathlib import Path

import pytest

from asclepias_broker.broker import SoftwareBroker
from helpers import generate_payloads


@pytest.fixture(scope='function')
def broker(request):
    b = SoftwareBroker()
    if request.param:
        for evt in generate_payloads(request.param):
            b.handle_event(evt)
    yield b


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
    return base_dir / 'jsonschema'


@pytest.fixture
def event_schema(schema_dir):
    with open(schema_dir / 'event.json', 'r') as fp:
        return json.load(fp)
