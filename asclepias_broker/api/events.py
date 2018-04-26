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

from ..jsonschemas import EVENT_SCHEMA
from ..models import Event
from ..schemas.loaders import RelationshipSchema
from ..tasks import process_event


class EventAPI:
    """Event API."""

    @classmethod
    def handle_event(cls, event: dict):
        """Handle an event payload."""
        # Raises JSONSchema ValidationError
        jsonschema.validate(event, EVENT_SCHEMA)

        # Validate the entries in the payload
        for payload in event:
            errors = RelationshipSchema(check_existing=True).validate(payload)
            if errors:
                raise MarshmallowValidationError(errors)

        event_obj = Event(payload=event)
        db.session.add(event_obj)
        db.session.commit()
        event_uuid = str(event_obj.id)
        process_event.delay(event_uuid)
