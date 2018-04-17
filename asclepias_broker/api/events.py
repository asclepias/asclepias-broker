# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 CERN.
#
# Asclepias Broker is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
"""Events API."""


import jsonschema
from invenio_db import db
from marshmallow.exceptions import \
    ValidationError as MarshmallowValidationError

from ..indexer import update_indices
from ..jsonschemas import EVENT_SCHEMA
from ..models import ObjectEvent, PayloadType
from ..schemas.loaders import EventSchema, RelationshipSchema
from ..tasks import process_event
from .ingestion import update_groups, update_metadata


class EventAPI:
    """Event API."""

    @classmethod
    def handle_event(cls, event: dict):
        """Handle an event payload."""
        jsonschema.validate(event, EVENT_SCHEMA)

        event_type = event['EventType']
        # TODO: Remove relationship_deleted handler and simplify the code here
        handlers = {
            "RelationshipCreated": cls.relationship_created,
            "RelationshipDeleted": cls.relationship_deleted,
        }
        handler = handlers[event_type]
        handler(event)

    @classmethod
    def create_event(cls, event: dict):
        """Create the event database model."""
        event_obj, errors = EventSchema(check_existing=True).load(event)
        if errors:
            raise MarshmallowValidationError(errors)

        # Validate the entries in the payload
        for payload in event['Payload']:
            errors = RelationshipSchema(check_existing=True).validate(payload)
            if errors:
                raise MarshmallowValidationError(errors)

        db.session.add(event_obj)
        return event_obj

    @classmethod
    def relationship_created(cls, event: dict):
        """Handle a relationship creation event."""
        cls._handle_relationship_event(event)

    @classmethod
    def relationship_deleted(cls, event: dict):
        """Handle a relationship deletion event."""
        cls._handle_relationship_event(event, delete=True)

    @classmethod
    def _handle_relationship_event(cls, event: dict, delete=False):
        event_obj = cls.create_event(event)
        event_uuid = str(event_obj.id)
        db.session.commit()
        process_event.delay(event_uuid)
