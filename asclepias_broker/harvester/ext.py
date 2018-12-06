# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 CERN.
#
# Asclepias Harvester is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Harvester extension."""

from typing import List, Tuple

from flask import current_app
from invenio_queues.proxies import current_queues
from werkzeug.utils import cached_property

from . import config
from ..events.signals import event_processed
from ..utils import obj_or_import_string
from .receivers import harvest_metadata_after_event_process
from .utils import HarvesterHistory


class AsclepiasHarvester:
    """Asclepias harvester extension."""

    def __init__(self, app=None):
        """Extension initialization."""
        if app:
            self.init_app(app)

    @cached_property
    def metadata_queue(self):
        """."""
        return current_queues.queues[self.metadata_queue_name]

    def publish_metadata_harvest(self, identifiers: List[Tuple[str, str]]):
        """Publish metadata harvesting jobs."""
        self.metadata_queue.publish(identifiers)

    @cached_property
    def history(self):
        """."""
        return HarvesterHistory(
            prefix=current_app.config['ASCLEPIAS_HARVESTER_HISTORY_PREFIX'])

    @staticmethod
    def _load_harvester_config(config_key):
        """."""
        harvesters_cfg = current_app.config[config_key]
        harvesters = {}
        for h_id, (h_cls, h_cfg) in harvesters_cfg.items():
            h_cls = obj_or_import_string(h_cls)
            h_cfg = obj_or_import_string(h_cfg, default={})
            if callable(h_cfg):
                h_cfg = h_cfg()
            harvesters[h_id] = h_cls(**h_cfg)
        return harvesters

    @cached_property
    def metadata_harvesters(self):
        """."""
        return self._load_harvester_config(
            'ASCLEPIAS_HARVESTER_METADATA_HARVESTERS')

    @cached_property
    def event_harvesters(self):
        """."""
        return self._load_harvester_config(
            'ASCLEPIAS_HARVESTER_EVENT_HARVESTERS')

    def init_app(self, app):
        """Flask application initialization."""
        self.init_config(app)

        self.metadata_queue_name = \
            app.config['ASCLEPIAS_HARVESTER_METADATA_QUEUE']
        self.mq_exchange = app.config['ASCLEPIAS_HARVESTER_MQ_EXCHANGE']

        if app.config['ASCLEPIAS_HARVESTER_HARVEST_AFTER_EVENT_PROCESS']:
            event_processed.connect(
                harvest_metadata_after_event_process, sender=app)
        app.extensions['asclepias-harvester'] = self

    @staticmethod
    def init_config(app):
        """Initialize configuration."""
        for k in dir(config):
            if k.startswith('ASCLEPIAS_HARVESTER_'):
                app.config.setdefault(k, getattr(config, k))
