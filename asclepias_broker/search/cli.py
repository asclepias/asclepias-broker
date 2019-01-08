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
@click.option('--destroy', default=False, is_flag=True)
@click.option('--split/--no-split', default=True)
@click.option('-e', '--eager', default=False, is_flag=True)
@click.confirmation_option(
    prompt='Are you sure you want to reindex everything?')
@with_appcontext
def reindex(destroy=False, split=True, eager=False):
    """Reindex all relationships."""
    task = reindex_all_relationships.s(destroy=destroy, split=split)
    if eager:
        task.apply(throw=True)
    else:
        task.apply_async()
