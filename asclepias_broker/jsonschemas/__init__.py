# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 CERN.
#
# Asclepias Broker is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
"""JSON Schemas of the Asclepias broker."""

import json
import os

_CUR_DIR = os.path.dirname(__file__)

with open(os.path.join(_CUR_DIR, 'scholix-v3.json'), 'r') as fp:
    SCHOLIX_SCHEMA = json.load(fp)

with open(os.path.join(_CUR_DIR, 'event.json'), 'r') as fp:
    EVENT_SCHEMA = json.load(fp)

_SCHOLIX_REL_TYPE = SCHOLIX_SCHEMA['properties']['RelationshipType']
SCHOLIX_RELATIONS = _SCHOLIX_REL_TYPE['properties']['Name']['enum']
