# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 CERN.
#
# Asclepias Broker is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Harvesting CLI."""

from __future__ import absolute_import, print_function
import datetime

from typing import List

import click
from ..monitoring.models import HarvestMonitoring, HarvestStatus
from ..harvester.tasks import harvest_metadata_identifier
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
        task.apply_async()


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
        task.apply_async()

@harvester.command('rerun')
@click.option('-i','--id', default=None)
@click.option('--start-time', default=None)
@click.option('--end-time', default=None)
@click.option('-a', '--all', default=False, is_flag=True)
@click.option('-e', '--errors', default=False, is_flag=True)
@click.option('-p', '--processing', default=False, is_flag=True)
@click.option('--no-index', default=False, is_flag=True)
@click.option('--eager', default=False, is_flag=True)
@with_appcontext
def rerun(id: str = None, all: bool = False, errors: bool = True, processing: bool = False,
    start_time: str = None, end_time:str = None, no_index: bool = False, eager: bool = False):
    """Rerun failed or stuck events."""
    if id:
        rerun_id(id, no_index, eager)
        return
    if all:
        errors = True
        processing = True
    if processing:
        rerun_processing(no_index, eager)
        rerun_new(no_index, eager)
    if errors:
        rerun_errors(no_index, eager, start_time, end_time)

def rerun_id(id:str, no_index: bool, eager:bool = False):
        event = HarvestMonitoring.get(id)
        if event:
            rerun_event(event, no_index=no_index, eager=eager)

def rerun_processing(no_index: bool, eager:bool = False):
        yesterday = datetime.datetime.now() - datetime.timedelta(days = 1)
        resp = HarvestMonitoring.query.filter(HarvestMonitoring.status == HarvestStatus.Processing, HarvestMonitoring.created < str(yesterday)).all()
        for event in resp:
            rerun_event(event, no_index=no_index, eager=eager)

def rerun_new(no_index: bool, eager:bool = False):
        yesterday = datetime.datetime.now() - datetime.timedelta(days = 1)
        resp = HarvestMonitoring.query.filter(HarvestMonitoring.status == HarvestStatus.New, HarvestMonitoring.created < str(yesterday)).all()
        for event in resp:
            rerun_event(event, no_index=no_index, eager=eager)

def rerun_errors(no_index: bool, eager:bool = False,  start_time: str = None, end_time:str = None):
        if start_time and end_time:
            resp = HarvestMonitoring.query.filter(HarvestMonitoring.status == HarvestStatus.Error, HarvestMonitoring.created > start_time, HarvestMonitoring.created < end_time).all()
        elif start_time:
            resp = HarvestMonitoring.query.filter(HarvestMonitoring.status == HarvestStatus.Error, HarvestMonitoring.created > start_time).all()
        elif end_time:
            resp = HarvestMonitoring.query.filter(HarvestMonitoring.status == HarvestStatus.Error, HarvestMonitoring.created < end_time).all()
        else:
            resp = HarvestMonitoring.query.filter(HarvestMonitoring.status == HarvestStatus.Error).all()
        for event in resp:
            rerun_event(event, no_index=no_index, eager=eager)

def rerun_event(event: HarvestMonitoring, no_index: bool, eager:bool = False):
        event_uuid = str(event.id)
        task = harvest_metadata_identifier.s(str(event.harvester), event.identifier, event.scheme,
                        event_uuid, None)
        if eager:
            task.apply(throw=True)
        else:
            task.apply_async()
        return event