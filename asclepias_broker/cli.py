# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 CERN.
#
# Asclepias Broker is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""CLI for Asclepias broker."""

from __future__ import absolute_import, print_function

import click
from flask.cli import with_appcontext


@click.group()
def utils():
    """Utility CLI commands."""


@utils.command('reindex')
@with_appcontext
def _reindex_all_relationships():
    """Reindex all relationships."""
    from .tasks import reindex_all_relationships
    reindex_all_relationships.delay()
