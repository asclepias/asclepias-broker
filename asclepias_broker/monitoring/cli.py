# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 CERN.
#
# Asclepias Broker is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Monitoring CLI."""

from __future__ import absolute_import, print_function

from typing import List

import click
from flask.cli import with_appcontext

from .tasks import sendMonitoringReport

@click.group()
def monitor():
    """Monitoring CLI commands."""


@monitor.command('report')
@click.option('-e', '--eager', default=False, is_flag=True)
@with_appcontext
def metadata_command(eager: bool = False):
    """Send monitoring report"""
    # Detect identifier schemes
    task = sendMonitoringReport.s()
    if eager:
        task.apply(throw=True)
    else:
        task.apply_async()