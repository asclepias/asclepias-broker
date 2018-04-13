# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 CERN.
#
# Asclepias Broker is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

from invenio_db import db

from ..models import ObjectEvent, PayloadType
from ..schemas.loaders import EventSchema, RelationshipSchema
from ..tasks import update_groups, update_indices, update_metadata


def get_or_create(model, **kwargs):
    instance = model.query.filter_by(**kwargs)
    if instance:
        return instance
    else:
        instance = model(**kwargs)
        db.session.add(instance)
        return instance


class EventAPI:
    @classmethod
    def handle_event(cls, event):
        event_type = event['EventType']
        handlers = {
            "RelationshipCreated": cls.relationship_created,
            "RelationshipDeleted": cls.relationship_deleted,
        }
        handler = handlers[event_type]
        with db.session.begin_nested():
            handler(event)
        db.session.commit()

    @classmethod
    def create_event(cls, event):
        # TODO: Skip existing events?
        # TODO: Check `errors`
        event_obj, errors = EventSchema(check_existing=True).load(event)
        db.session.add(event_obj)
        return event_obj

    @classmethod
    def create_relation_object_events(cls, event, relationship, payload_idx):
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

    @classmethod
    def relationship_created(cls, event):
        cls._handle_relationship_event(event)

    @classmethod
    def relationship_deleted(cls, event):
        cls._handle_relationship_event(event, delete=True)

    # TODO: Test if this generalization works as expected
    @classmethod
    def _handle_relationship_event(cls, event, delete=False):
        event_obj = cls.create_event(event)
        for payload_idx, payload in enumerate(event['Payload']):
            with db.session.begin_nested():
                relationship, errors = RelationshipSchema(check_existing=True).load(payload)
                if errors:
                    # TODO: Add better error handling
                    raise ValueError(errors)
                if relationship.id:
                    relationship.deleted = delete
                db.session.add(relationship)
                # We need ORM relationship with IDs, since Event has
                # 'weak' (non-FK) relations to the objects, hence we need
                # to know the ID upfront
                relationship = relationship.fetch_or_create_id()
                cls.create_relation_object_events(
                    event_obj, relationship, payload_idx)

                # TODO: This should be a task after the ingestion commit
                groups = update_groups(relationship)
                src_grp, tar_grp, merged_grp = groups
                # Update metadata
                update_metadata(relationship, payload)
                # Index the groups and relationships
                update_indices(src_grp, tar_grp, merged_grp)
