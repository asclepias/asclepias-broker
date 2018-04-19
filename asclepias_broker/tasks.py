# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 CERN.
#
# Asclepias Broker is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Asynchronous tasks."""

from celery import shared_task
from invenio_db import db
from marshmallow.exceptions import \
    ValidationError as MarshmallowValidationError

from .api.ingestion import update_groups, update_metadata
from .indexer import update_indices
from .models import Event, ObjectEvent, PayloadType
from .schemas.loaders import RelationshipSchema


def get_or_create(model, **kwargs):
    """Get or a create a database model."""
    instance = model.query.filter_by(**kwargs)
    if instance:
        return instance
    else:
        instance = model(**kwargs)
        db.session.add(instance)
        return instance


def create_relation_object_events(event, relationship, payload_idx):
    """Create the object event models."""
    # Create the Relation entry
    rel_obj = get_or_create(
        ObjectEvent,
        event_id=event.id,
        object_uuid=relationship.id,
        payload_type=PayloadType.Relationship,
        payload_index=payload_idx)

    # Create entries for source and target
    src_obj = get_or_create(
        ObjectEvent,
        event_id=event.id,
        object_uuid=relationship.source.id,
        payload_type=PayloadType.Identifier,
        payload_index=payload_idx)
    tar_obj = get_or_create(
        ObjectEvent,
        event_id=event.id,
        object_uuid=relationship.target.id,
        payload_type=PayloadType.Identifier,
        payload_index=payload_idx)
    return rel_obj, src_obj, tar_obj


@shared_task(ignore_result=True)
def process_event(event_uuid: str, delete=False):
    """Process an event's payloads."""
    # TODO: Should we detect and skip duplicated events?
    event = Event.get(event_uuid)
    # TODO: event.payload contains the whole event, not just payload - refactor
    with db.session.begin_nested():
        for payload_idx, payload in enumerate(event.payload['Payload']):
            # TODO: marshmallow validation of all payloads
            # should be done on first event ingestion (check)
            relationship, errors = \
                RelationshipSchema(check_existing=True).load(payload)
            # Errors should never happen as the payload is validated
            # with RelationshipSchema on the event ingestion
            if errors:
                raise MarshmallowValidationError(errors)
            if relationship.id:
                relationship.deleted = delete
            db.session.add(relationship)
            # We need ORM relationship with IDs, since Event has
            # 'weak' (non-FK) relations to the objects, hence we need
            # to know the ID upfront
            relationship = relationship.fetch_or_create_id()
            create_relation_object_events(event, relationship, payload_idx)

            id_groups, version_groups = update_groups(relationship)

            update_metadata(relationship, payload)

            update_indices(*id_groups)
            update_indices(*version_groups)
    db.session.commit()
