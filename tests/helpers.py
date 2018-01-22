import pytest
import os
import json

#
# JSON schema and test data loading fixtures
#
@pytest.fixture
def test_dir():
    return os.path.dirname(__file__)


@pytest.fixture
def data_dir(test_dir):
    return os.path.join(test_dir, 'data')
