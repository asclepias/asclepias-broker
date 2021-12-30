# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 CERN.
#
# Asclepias Broker is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

FROM nginx
COPY nginx.conf /etc/nginx/nginx.conf
COPY conf.d/* /etc/nginx/conf.d/
COPY fullchain.pem /etc/letsencrypt/live/asclepias-broker.aas.org/fullchain.pem
COPY privkey.pem /etc/letsencrypt/live/asclepias-broker.aas.org/privkey.pem