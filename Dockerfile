# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 CERN.
#
# Asclepias Broker is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#F§ROM inveniosoftware/centos7-python:3.6
FROM python:3.8

RUN mkdir /app
WORKDIR /app

COPY Pipfile Pipfile
#COPY Pipfile.lock Pipfile.lock
RUN pip install pipenv
#RUN pipenv install --deploy --system
RUN pipenv install --ignore-pipfile 
ADD . /app
RUN pipenv install .

#CMD ["./keepMeAlive.sh"]
CMD ["asclepias-broker", "shell"]
