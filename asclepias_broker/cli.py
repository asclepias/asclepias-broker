# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 CERN.
#
# Asclepias Broker is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""CLI for Asclepias broker."""

from __future__ import absolute_import, print_function

import glob
import json
from datetime import datetime

import click
from flask.cli import with_appcontext
from invenio_db import db

from .api.ingestion import get_group_from_id


@click.group()
def utils():
    """Utility CLI commands."""


@utils.command('reindex')
@click.option('--no-celery', default=False, is_flag=True)
@with_appcontext
def reindex(no_celery=False):
    """Reindex all relationships."""
    from .tasks import reindex_all_relationships
    if no_celery:
        reindex_all_relationships()
    else:
        reindex_all_relationships.delay()


def find_json(dirpath):
    """Finds all JSON files in given subdirectory."""
    out = glob.glob(dirpath + "/**/*.json", recursive=True)
    return out


@utils.command('load')
@click.argument('jsondir', type=click.Path(exists=True, dir_okay=True,
                                           resolve_path=True))
@click.option('--no-index', default=False, is_flag=True)
@with_appcontext
def load(jsondir, no_index=False):
    """Load events from a directory."""
    from .api.events import EventAPI
    files = find_json(jsondir)
    with click.progressbar(files) as bar_files:
        for fn in bar_files:
            with open(fn, 'r') as fp:
                data = json.load(fp)
            try:
                EventAPI.handle_event(data, no_index=no_index)
            except ValueError:
                pass


@utils.command('update_metadata')
@click.argument('jsondir', type=click.Path(exists=True, dir_okay=True,
                                           resolve_path=True))
@with_appcontext
def update_metadata(jsondir):
    """Load events from a directory."""
    files = find_json(jsondir)
    with click.progressbar(files) as bar_files:
        for fn in bar_files:
            with open(fn, 'r') as fp:
                data = json.load(fp)
            update_groups(data)


def update_groups(data):
    """Update groups and the Identity group's metadata."""
    from .api.events import EventAPI

    provider = data.get('Provider')
    identifiers = data.get('Object').get('Identifier')
    event = []
    source_identifier = identifiers.pop()
    for identifier in identifiers:
        payload = {
            "RelationshipType": {
                "Name": "IsRelatedTo",
                "SubTypeSchema": "DataCite",
                "SubType": "IsIdenticalTo"
            },
            "Target": {
                "Identifier": identifier,
                "Type": {
                    "Name": "unknown"
                }
            },
            "LinkProvider": [
                {
                    "Name": provider
                }
            ],
            "Source": {
                "Identifier": source_identifier,
                "Type": {
                    "Name": "unknown"
                }
            },
            "LinkPublicationDate": str(datetime.now())
        }
        event.append(payload)
    try:
        EventAPI.handle_event(event, no_index=True, delayed=False)
    except ValueError:
        pass

    try:
        group = get_group_from_id(
            identifiers[0]['ID'], identifiers[0]['IDScheme'])
        if group:
            group.data.update(data.get('Object'))
        db.session.commit()
    except Exception:
        pass
