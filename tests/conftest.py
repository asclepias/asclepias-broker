# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 CERN.
#
# Asclepias Broker is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
"""Putest configuration and fixtures."""

import json
import os

import pytest
from invenio_app.factory import create_api


@pytest.fixture(scope='module')
def create_app():
    """Application factory to be used by ``pytest-invenio``."""
    return create_api


#
# JSON schema and test data loading fixtures
#
@pytest.fixture
def tests_dir():
    """The package's ``tests`` directory."""
    return os.path.dirname(__file__)


@pytest.fixture
def data_dir(tests_dir):
    """Test ``data`` directory."""
    return os.path.join(tests_dir, 'data')


@pytest.fixture
def base_dir(tests_dir):
    """Package directory."""
    return os.path.dirname(tests_dir)


@pytest.fixture
def examples_dir(base_dir):
    """Package ``examples`` directory."""
    return os.path.join(base_dir, 'examples')


@pytest.fixture
def example_events(examples_dir):
    """Event payloads from the ``examples`` directory."""
    filenames = [
        'ads-events.json',
        'test-events.json',
    ]
    data = []
    for fn in filenames:
        with open(os.path.join(examples_dir, fn), 'r') as fp:
            data.append(json.load(fp))
    return data
