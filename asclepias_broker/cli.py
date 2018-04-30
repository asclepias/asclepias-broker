# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 CERN.
#
# Asclepias Broker is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""CLI for Asclepias broker."""

from __future__ import absolute_import, print_function

import glob
import click
import json
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


def find_json(dirpath):
    """Finds all JSON files in given subdirectory."""
    out = glob.glob(dirpath + "/**/*.json", recursive=True)
    return out


@utils.command('load')
@click.argument('jsondir', type=click.Path(exists=True, dir_okay=True,
                                           resolve_path=True))
@click.option('--no-index')
@with_appcontext
def load_events(jsondir, no_index=False):
    """Load events from a directory."""
    from .api.events import EventAPI
    files = find_json(jsondir)
    with click.progressbar(files) as bar_files:
        for fn in bar_files:
            with open(fn, 'r') as fp:
                data = json.load(fp)
            EventAPI.handle_event(data, no_index=no_index)
