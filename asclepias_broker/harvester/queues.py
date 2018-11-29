# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 CERN.
#
# Asclepias Harvester is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Harvester queues."""

from .proxies import current_harvester


def declare_queues():
    """Index statistics events."""
    return [{
        'name': current_harvester.metadata_queue_name,
        'exchange': current_harvester.mq_exchange,
    }]
