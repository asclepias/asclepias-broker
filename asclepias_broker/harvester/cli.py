# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 CERN.
#
# Asclepias Broker is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Harvesting CLI."""

from __future__ import absolute_import, print_function

from typing import List

import click
import idutils
from flask.cli import with_appcontext

from .tasks import harvest_events, harvest_metadata


@click.group()
def harvester():
    """Harvesting CLI commands."""


@harvester.command('metadata')
@click.argument('identifiers', nargs=-1, metavar='[IDENTIFIER]...')
@click.option('-e', '--eager', default=False, is_flag=True)
@with_appcontext
def metadata_command(identifiers: List[str], eager: bool = False):
    """Harvest metadata."""
    # Detect identifier schemes
    identifiers = [(i, idutils.detect_identifier_schemes(i)[0])
                   for i in identifiers]
    task = harvest_metadata.s(identifiers, eager=eager)
    if eager:
        task.apply(throw=True)
    else:
        task.apply_async(throw=True)


@harvester.command('events')
@click.argument('harvester_ids', nargs=-1, metavar='[HARVESTER-ID]...')
@click.option('-e', '--eager', default=False, is_flag=True)
@with_appcontext
def events_command(harvester_ids: List[str], eager: bool = False):
    """Harvest events."""
    task = harvest_events.s(harvester_ids, eager=eager)
    if eager:
        task.apply(throw=True)
    else:
        task.apply_async(throw=True)
