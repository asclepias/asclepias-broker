# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 CERN.
#
# Asclepias Broker is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""CLI for Asclepias broker search module."""

from __future__ import absolute_import, print_function

import click
from flask.cli import with_appcontext

from .tasks import reindex_all_relationships


@click.group()
def search():
    """Utility CLI commands."""


@search.command('reindex')
@click.option('--no-celery', default=False, is_flag=True)
@with_appcontext
def reindex(no_celery=False):
    """Reindex all relationships."""
    if no_celery:
        reindex_all_relationships()
    else:
        reindex_all_relationships.delay()
