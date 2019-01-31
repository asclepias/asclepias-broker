# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 CERN.
#
# Asclepias Broker is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
"""Events API."""

import jsonschema
from flask import current_app
from invenio_db import db
from marshmallow.exceptions import \
    ValidationError as MarshmallowValidationError
from werkzeug.local import LocalProxy

from ..graph.tasks import process_event
from ..jsonschemas import EVENT_SCHEMA, SCHOLIX_SCHEMA
from ..schemas.loaders import RelationshipSchema
from .models import Event, EventStatus


def _jsonschema_validator_func():
    schema_host = current_app.config['JSONSCHEMAS_HOST']
    schema_store = {
        f'{schema_host}/scholix-v3.json': SCHOLIX_SCHEMA,
        f'{schema_host}/event.json': EVENT_SCHEMA,
    }
    resolver = jsonschema.RefResolver(
        schema_host, EVENT_SCHEMA, schema_store)
    return jsonschema.Draft4Validator(EVENT_SCHEMA, resolver=resolver)


class EventAPI:
    """Event API."""

    _jsonschema_validator = LocalProxy(_jsonschema_validator_func)
    """Event JSONSchema validator."""

    @classmethod
    def validate_payload(cls, event):
        """Validate the event payload."""
        # TODO: Use invenio-jsonschemas/jsonresolver instead of this
        # Validate against Event JSONSchema
        # NOTE: raises `jsonschemas.ValidationError`
        cls._jsonschema_validator.validate(event)

        # Validate using marshmallow loader
        for payload in event:
            errors = RelationshipSchema(check_existing=True).validate(payload)
            if errors:
                raise MarshmallowValidationError(errors)

    @classmethod
    def handle_event(cls, event: dict, no_index: bool = False,
                     user_id: int = None, eager: bool = False) -> Event:
        """Handle an event payload."""
        cls.validate_payload(event)
        event_obj = Event(payload=event, status=EventStatus.New,
                          user_id=user_id)
        db.session.add(event_obj)
        db.session.commit()
        event_uuid = str(event_obj.id)
        idx_enabled = current_app.config['ASCLEPIAS_SEARCH_INDEXING_ENABLED'] \
            and (not no_index)
        task = process_event.s(
            event_uuid=event_uuid, indexing_enabled=idx_enabled)
        if eager:
            task.apply(throw=True)
        else:
            task.apply_async()
        return event_obj
