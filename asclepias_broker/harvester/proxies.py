# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 CERN.
#
# Asclepias Harvester is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Harvester proxies."""

from flask import current_app
from werkzeug.local import LocalProxy

current_harvester = LocalProxy(
    lambda: current_app.extensions['asclepias-harvester'])
