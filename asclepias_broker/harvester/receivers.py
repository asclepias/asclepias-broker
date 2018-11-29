# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 CERN.
#
# Asclepias Broker is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
"""Signal receivers."""

from ..events.models import Event, PayloadType
from .proxies import current_harvester
from .tasks import harvest_metadata


def harvest_metadata_after_event_process(app, event: Event = None):
    """."""
    identifiers = set()
    identifier_events = (obj_event for obj_event in event.object_events
                         if obj_event.payload_type == PayloadType.Identifier)
    for id_event in identifier_events:
        # Check provider to avoid self-triggering harvesting
        scholix_payload = event.payload[id_event.payload_index]
        provider = scholix_payload.get('LinkProvider', [{}])[0].get('Name')
        if provider != current_harvester.provider_name:
            identifier = id_event.object
            identifiers.add((identifier.value, identifier.scheme))
    if identifiers:
        harvest_metadata.delay(list(identifiers))
