# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 CERN.
#
# Asclepias Broker is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Asynchronous tasks."""

from typing import Dict, List, Set, Tuple

import datetime
from celery import shared_task
from flask import current_app
from invenio_db import db
from marshmallow.exceptions import \
    ValidationError as MarshmallowValidationError

from ..core.models import Relationship
from ..events.models import Event, EventStatus, ObjectEvent, PayloadType
from ..events.signals import event_processed
from ..metadata.api import update_metadata_from_event
from ..schemas.loaders import RelationshipSchema
from ..search.indexer import update_indices
from .api import update_groups
from ..events.cli import rerun_event
from ..monitoring.models import ErrorMonitoring


def get_or_create(model, **kwargs):
    """Get or a create a database model."""
    instance = model.query.filter_by(**kwargs).one_or_none()
    if instance:
        return instance
    else:
        instance = model(**kwargs)
        db.session.add(instance)
        return instance


def create_relation_object_events(
    event: Event,
    relationship: Relationship,
    payload_idx: int
):
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


def compact_indexing_groups(
    groups_ids: List[Tuple[str, str, str, str, str, str]]
) -> Tuple[
    Set[str], Set[str],
    Set[str], Set[str],
    Dict[str, str],
]:
    """Compact the collected group IDs into minimal set of UUIDs."""
    # Compact operations
    ig_to_vg_map = {}
    id_groups_to_index = set()
    ver_groups_to_index = set()
    id_groups_to_delete = set()
    ver_groups_to_delete = set()
    for src_ig, trg_ig, mrg_ig, src_vg, trg_vg, mrg_vg in groups_ids:
        ig_to_vg_map[src_ig] = src_vg
        ig_to_vg_map[trg_ig] = trg_vg
        ig_to_vg_map[mrg_ig] = mrg_vg
        if not mrg_ig:
            id_groups_to_index |= {src_ig, trg_ig}
        else:
            id_groups_to_index.add(mrg_ig)
            id_groups_to_delete |= {src_ig, trg_ig}

        if not mrg_vg:
            ver_groups_to_index |= {src_vg, trg_vg}
        else:
            ver_groups_to_index.add(mrg_vg)
            ver_groups_to_delete |= {src_vg, trg_vg}
    id_groups_to_index -= id_groups_to_delete
    ver_groups_to_index -= ver_groups_to_delete
    return (id_groups_to_index, id_groups_to_delete, ver_groups_to_index,
            ver_groups_to_delete, ig_to_vg_map)


def _set_event_status(event_uuid, status):
    """Set the status of the Event."""
    event = Event.get(event_uuid)
    event.status = status
    db.session.commit()


@shared_task(bind=True, ignore_result=True, max_retries=1, default_retry_delay=10 * 60)
def process_event(self, event_uuid: str, indexing_enabled: bool = True):
    """Process the event."""
    # TODO: Should we detect and skip duplicated events?
    _set_event_status(event_uuid, EventStatus.Processing)
    try:
        event = Event.get(event_uuid)
        groups_ids = []
        with db.session.begin_nested():
            for payload_idx, payload in enumerate(event.payload):
                # TODO: marshmallow validation of all payloads
                # should be done on first event ingestion (check)
                relationship = RelationshipSchema(check_existing=True).load(payload)
                # Errors should never happen as the payload is validated
                # with RelationshipSchema on the event ingestion

                # Skip already known relationships
                # NOTE: This skips any extra metadata!
                if relationship.id:
                    continue
                db.session.add(relationship)
                # We need ORM relationship with IDs, since Event has
                # 'weak' (non-FK) relations to the objects, hence we need
                # to know the ID upfront
                relationship = relationship.fetch_or_create_id()
                create_relation_object_events(event, relationship, payload_idx)
                id_groups, ver_groups = update_groups(relationship)

                update_metadata_from_event(relationship, payload)
                groups_ids.append(
                    [str(g.id) if g else g for g in id_groups + ver_groups])
        db.session.commit()

        if indexing_enabled:
            compacted = compact_indexing_groups(groups_ids)
            update_indices(*compacted)

        _set_event_status(event_uuid, EventStatus.Done)
        event_processed.send(current_app._get_current_object(), event=event)
    except Exception as exc:
        db.session.rollback()
        _set_event_status(event_uuid, EventStatus.Error)
        payload = Event.get(id=event_uuid).payload
        error_obj = ErrorMonitoring(origin=self.__class__.__name__, error=repr(exc), n_retries=self.request.retries, payload=payload)
        db.session.add(error_obj)
        db.session.commit()
        self.retry(exc=exc)

@shared_task(ignore_result=True)
def rerun_errors():
    two_days_ago = datetime.datetime.now() - datetime.timedelta(days = 2)
    resp = Event.query.filter(Event.status == EventStatus.Error, Event.created > str(two_days_ago)).all()
    for event in resp:
        rerun_event(event, no_index=True, eager=False)