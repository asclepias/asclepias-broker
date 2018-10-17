#!/usr/bin/env bash
# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 CERN.
#
# Asclepias Broker is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

# TODO: Fix when patched in Flask-Admin (or remove dependency)
pipenv check --ignore 36437 && \
pipenv run pydocstyle asclepias_broker tests docs && \
pipenv run isort -rc -c -df && \
pipenv run check-manifest --ignore ".travis-*,docs/_build*" && \
pipenv run sphinx-build -qnNW docs docs/_build/html && \
pipenv run test
