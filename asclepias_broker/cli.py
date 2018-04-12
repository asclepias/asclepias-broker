# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 CERN.
#
# Asclepias Broker is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

import click
from flask.cli import FlaskGroup
from .app import create_app


@click.group(cls=FlaskGroup, create_app=lambda _: create_app())
def cli():
    """CLI for Asclepias Broker"""
    pass


if __name__ == '__main__':
    cli()
