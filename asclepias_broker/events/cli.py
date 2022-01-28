# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 CERN.
#
# Asclepias Broker is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Events CLI."""

from __future__ import absolute_import, print_function
import datetime

import json

import click
from flask.cli import with_appcontext
from flask import current_app

from ..utils import find_ext
from .api import EventAPI
from ..graph.tasks import process_event
from .models import Event, EventStatus


@click.group()
def events():
    """Event CLI commands."""


@events.command('load')
@click.argument(
    'jsondir_or_file',
    type=click.Path(exists=True, dir_okay=True, resolve_path=True))
@click.option('--no-index', default=False, is_flag=True)
@click.option('-e', '--eager', default=False, is_flag=True)
@with_appcontext
def load(jsondir_or_file: str, no_index: bool = False, eager: bool = False):
    """Load events from a directory."""
    files = find_ext(jsondir_or_file, '.json')
    with click.progressbar(files) as bar_files:
        for fn in bar_files:
            with open(fn, 'r') as fp:
                data = json.load(fp)
            try:
                EventAPI.handle_event(data, no_index=no_index, eager=eager)
            except ValueError:
                pass

@events.command('rerun')
@click.option('-i','--id', default=None)
@click.option('-a', '--all', default=False, is_flag=True)
@click.option('-e', '--errors', default=False, is_flag=True)
@click.option('-p', '--processing', default=False, is_flag=True)
@click.option('--no-index', default=False, is_flag=True)
@click.option('--eager', default=False, is_flag=True)
@with_appcontext
def rerun(id: str = None, all: bool = False, errors: bool = True, processing: bool = False, no_index: bool = False, eager: bool = False):
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
        rerun_errors(no_index, eager)

def rerun_id(id:str, no_index: bool, eager:bool = False):
        event = Event.get(id)
        if event:
            EventAPI.rerun_event(event, no_index=no_index, eager=eager)

def rerun_processing(no_index: bool, eager:bool = False):
        yesterday = datetime.datetime.now() - datetime.timedelta(days = 1)
        resp = Event.query.filter(Event.status == EventStatus.Processing, Event.created < str(yesterday)).all()
        for event in resp:
            EventAPI.rerun_event(event, no_index=no_index, eager=eager)

def rerun_new(no_index: bool, eager:bool = False):
        yesterday = datetime.datetime.now() - datetime.timedelta(days = 1)
        resp = Event.query.filter(Event.status == EventStatus.New, Event.created < str(yesterday)).all()
        for event in resp:
            EventAPI.rerun_event(event, no_index=no_index, eager=eager)

def rerun_errors(no_index: bool, eager:bool = False):
        resp = Event.query.filter(Event.status == EventStatus.Error).all()
        for event in resp:
            EventAPI.rerun_event(event, no_index=no_index, eager=eager)