# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 CERN.
#
# Asclepias Broker is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Pytest fixtures and plugins for the API application."""

from __future__ import absolute_import, print_function

import pytest
from invenio_app.factory import create_api
# FIXME: This is bad... invenio-oauth2server changes behavior since there is
# an import-order-dependent loading of some decorators:
# https://github.com/inveniosoftware/invenio-oauth2server/blob/master/invenio_oauth2server/views/server.py#L36-L44
from invenio_oauth2server.views.server import oauth2


@pytest.fixture(scope='module')
def create_app():
    """."""
    return create_api
