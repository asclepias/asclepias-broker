# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 CERN.
#
# Asclepias Broker is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
FROM inveniosoftware/centos7-python:3.6

RUN mkdir /app
WORKDIR /app

COPY Pipfile Pipfile
COPY Pipfile.lock Pipfile.lock
RUN pipenv install --deploy --system

ADD . /app
RUN pip install .

CMD ["asclepias-broker", "shell"]
