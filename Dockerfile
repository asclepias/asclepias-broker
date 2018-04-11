# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 CERN.
#
# Asclepias Broker is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

FROM python:3.5

RUN apt-get update -y && apt-get upgrade -y
RUN apt-get install -y git curl vim
RUN pip install --upgrade setuptools wheel pip uwsgi

# Install Node
RUN curl -sL https://deb.nodesource.com/setup_6.x | bash -
RUN apt-get install -y nodejs
RUN npm update

RUN python -m site
RUN python -m site --user-site

# Install Invenio
ENV WORKING_DIR=/opt/asclepias-broker
ENV INVENIO_INSTANCE_PATH=${WORKING_DIR}/var/instance

# copy everything inside /src
RUN mkdir -p ${WORKING_DIR}/src
COPY ./ ${WORKING_DIR}/src
WORKDIR ${WORKING_DIR}/src

# Install Python dependencies
ARG ENVIRONMENT=DEV
RUN if [ "$ENVIRONMENT" = "DEV" ]; then pip install -e .[all]; fi;
RUN if [ "$ENVIRONMENT" = "PROD" ]; then pip install -r requirements-pinned.txt; fi;

# Install/create static files
RUN mkdir -p ${INVENIO_INSTANCE_PATH}
RUN ./scripts/setup-npm.sh && \
    asclepias-broker npm && \
    cd ${INVENIO_INSTANCE_PATH}/static && \
    npm install && \
    asclepias-broker collect -v && \
    asclepias-broker assets build

# copy uwsgi config files
COPY ./docker/uwsgi/ ${INVENIO_INSTANCE_PATH}

# Set folder permissions
RUN chgrp -R 0 ${INVENIO_INSTANCE_PATH} && \
    chmod -R g=u ${INVENIO_INSTANCE_PATH}

RUN useradd invenio --uid 1000 --gid 0 && \
    chown -R invenio:root ${INVENIO_INSTANCE_PATH}
USER 1000
