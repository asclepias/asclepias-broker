# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 CERN.
#
# Asclepias Broker is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Events CLI."""

from __future__ import absolute_import, print_function

import json

import click
from flask.cli import with_appcontext

from ..utils import find_ext
from .api import EventAPI


@click.group()
def events():
    """Utility CLI commands."""


@events.command('load')
@click.argument(
    'jsondir_or_file',
    type=click.Path(exists=True, dir_okay=True, resolve_path=True))
@click.option('--no-index', default=False, is_flag=True)
@click.option('--eager', default=False, is_flag=True)
@with_appcontext
def load(jsondir_or_file: str, no_index: bool = False, eager: bool = False):
    """Load events from a directory."""
    files = find_ext(jsondir_or_file, '.json')
    with click.progressbar(files) as bar_files:
        for fn in bar_files:
            with open(fn, 'r') as fp:
                data = json.load(fp)
            try:
                EventAPI.handle_event(
                    data, no_index=no_index, delayed=(not eager))
            except ValueError:
                pass
