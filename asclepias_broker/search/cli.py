# -*- coding: utf-8 -*-
#
# Copyright (C) 2018-2019 CERN.
#
# Asclepias Broker is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""CLI for Asclepias broker search module."""

from __future__ import absolute_import, print_function

import click
from flask.cli import with_appcontext

from .tasks import reindex_all_relationships
from .utils import rollover_indices


@click.group()
def search():
    """Utility CLI commands."""


@search.command('reindex')
@click.option('--rollover/--no-rollover', default=True, is_flag=True)
@click.option('--split/--no-split', default=True)
@click.option('-e', '--eager', default=False, is_flag=True)
@click.confirmation_option(
    prompt='Are you sure you want to reindex everything?')
@with_appcontext
def reindex(rollover=True, split=True, eager=False):
    """Reindex all relationships."""
    task = reindex_all_relationships.s(rollover=rollover, split=split)
    if eager:
        task.apply(throw=True)
    else:
        task.apply_async()
    click.secho('Reindexing has been processed.', fg='green')


@search.command('rollover')
@click.option('--keep-old-indices', type=int, default=1,
              help='Number of old indices to keep.')
@click.confirmation_option(
    prompt='Are you sure you want to rollover the indices?')
@with_appcontext
def rollover(keep_old_indices=1):
    """Rollover indices."""
    rollover_indices(keep_old_indices)
