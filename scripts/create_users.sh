#!/usr/bin/env bash
# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 CERN.
#
# Asclepias Broker is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

set -e

# Create admin role to rectict access
export SQLALCHEMY_DATABASE_URI='postgresql+psycopg2://asclepias:asclepias@localhost/asclepias'
invenio users create admin@cern.ch -a --password=123456
invenio roles create admin
invenio roles add admin@asclepias.org admin
invenio access allow superuser-access role admin
