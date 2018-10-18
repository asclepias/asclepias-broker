# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 CERN.
#
# Asclepias Broker is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""CLI for Asclepias broker."""

from __future__ import absolute_import, print_function

import json
from datetime import datetime

import click
from flask.cli import with_appcontext
from invenio_db import db

from ..events.api import EventAPI
from ..graph.api import get_group_from_id
from ..utils import find_ext


@click.group()
def metadata():
    """Utility CLI commands."""


@metadata.command('load')
@click.argument(
    'jsondir', type=click.Path(exists=True, dir_okay=True, resolve_path=True))
@with_appcontext
def load_metadata(jsondir):
    """Load events from a directory."""
    files = find_ext(jsondir, 'json')
    with click.progressbar(files) as bar_files:
        for fn in bar_files:
            with open(fn, 'r') as fp:
                data = json.load(fp)
            update_groups(data)


def update_groups(data):
    """Update groups and the Identity group's metadata."""
    provider = data.get('Provider')
    identifiers = data.get('Object').get('Identifier')
    event = []
    source_identifier = identifiers.pop()
    for identifier in identifiers:
        payload = {
            'RelationshipType': {
                'Name': 'IsRelatedTo',
                'SubTypeSchema': 'DataCite',
                'SubType': 'IsIdenticalTo'
            },
            'Target': {
                'Identifier': identifier,
                'Type': {'Name': 'unknown'}
            },
            'LinkProvider': [
                {'Name': provider}
            ],
            'Source': {
                'Identifier': source_identifier,
                'Type': {'Name': 'unknown'}
            },
            "LinkPublicationDate": str(datetime.now()),
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
