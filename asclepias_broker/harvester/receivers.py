# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 CERN.
#
# Asclepias Broker is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
"""Signal receivers."""

from ..events.models import Event, PayloadType
from .proxies import current_harvester


def harvest_metadata_after_event_process(app, event: Event = None):
    """."""
    identifiers = set()
    identifier_events = (obj_event for obj_event in event.object_events
                         if obj_event.payload_type == PayloadType.Identifier)
    for id_event in identifier_events:
        # Check provider to avoid self-triggering harvesting
        scholix_payload = event.payload[id_event.payload_index]
        providers = [provider.get('Name') for provider in
                     scholix_payload.get('LinkProvider', [{}])]
        identifier = id_event.object
        identifiers.add((identifier.value, identifier.scheme,
                         frozenset(providers)))
    if identifiers:
        payloads = [
            dict(identifier=identifier, scheme=scheme,
                 providers=list(providers))
            for identifier, scheme, providers in identifiers
        ]
        current_harvester.publish_metadata_harvest(payloads)
