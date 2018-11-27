# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 CERN.
#
# Asclepias Broker is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""CLI for Asclepias broker."""

from __future__ import absolute_import, print_function

import json

import click
from flask.cli import with_appcontext

from ..utils import find_ext
from .api import update_metadata


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

            identifier = data['Identifier'][0]['ID']
            scheme = data['Identifier'][0]['IDScheme']
            provider = data.get('Provider')
            update_metadata(
                identifier, scheme, data['Object'], provider=provider)
