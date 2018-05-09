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

import click
from flask.cli import with_appcontext
from invenio_db import db

from .api.ingestion import get_group_from_id, update_group_metadata


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
    identifiers_ids = set([identifier.get('ID') for identifier in identifiers])

    is_identity_group_ok = False
    i = 0

    while not is_identity_group_ok and i < len(identifiers):
        try:
            identifier_id = identifiers[i].get('ID')
            group = get_group_from_id(identifier_value=identifier_id,
                                      id_type=identifiers[i].get('IDScheme'))
        except Exception:
            group = None

        if group is None:
            i = i + 1
        else:
            group_ids = set([identifier.value
                             for identifier in group.identifiers])
            if identifiers_ids.issubset(group_ids):
                is_identity_group_ok = True
            else:
                new_identifiers_ids = identifiers_ids - group_ids
                new_identifiers = [identifier for identifier in identifiers if
                                   identifier.get('ID') in new_identifiers_ids]
                event = [{
                    "RelationshipType": {
                        "Name": "IsRelatedTo",
                        "SubTypeSchema": "DataCite",
                        "SubType": "IsIdenticalTo"
                    },
                    "Target": {
                        "Identifier": new_identifiers[0],
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
                        "Identifier": identifiers[i],
                        "Type": {
                            "Name": "unknown"
                        }
                    },
                    "LinkPublicationDate": "2018-05-01"
                }]
                try:
                    EventAPI.handle_event(event, no_index=True, delayed=False)
                except ValueError:
                    pass
    try:
        update_group_metadata(identifiers[0], data.get('Object'))
        db.session.commit()
    except Exception:
        pass
