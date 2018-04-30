#!/usr/bin/env bash
# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 CERN.
#
# Asclepias Broker is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

set -e

npm update && npm install --silent -g node-sass@3.8.0 clean-css@3.4.19 uglify-js@2.7.3 requirejs@2.2.0

CWD=`pwd`
asclepias-broker npm
cd ${VIRTUAL_ENV}/var/instance/static
npm install
cd ${CWD}
asclepias-broker collect -v
asclepias-broker assets build
