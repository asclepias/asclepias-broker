# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 CERN.
# Copyright (c) 2017 Thomas P. Robitaille.
#
# Asclepias Broker is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
"""Event database models."""

import enum
import uuid
from typing import Union
import datetime

from invenio_accounts.models import User
from invenio_db import db
from sqlalchemy.schema import PrimaryKeyConstraint
from sqlalchemy_utils.models import Timestamp
from sqlalchemy_utils.types import JSONType, UUIDType
from sqlalchemy import func

from ..core.models import Identifier, Relationship


class EventStatus(enum.Enum):
    """Event status."""

    New = 1
    Processing = 2
    Error = 3
    Done = 4


class PayloadType(enum.Enum):
    """Payload type."""

    Relationship = 1
    Identifier = 2


class Event(db.Model, Timestamp):
    """Event model."""

    __tablename__ = 'event'

    id = db.Column(UUIDType, default=uuid.uuid4, primary_key=True)
    payload = db.Column(JSONType)

    status = db.Column(db.Enum(EventStatus), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey(User.id), nullable=True)

    user = db.relationship(User)

    @classmethod
    def get(cls, id: str = None, **kwargs):
        """Get the event from the database."""
        return cls.query.filter_by(id=id).one_or_none()
    
    @classmethod
    def getStatsFromLastWeek(cls):
        """Gets the stats from the last 7 days"""
        last_week = datetime.datetime.now() - datetime.timedelta(days = 7)
        resp = db.session.query(cls.status, func.count('*')).filter(cls.updated > str(last_week)).group_by(cls.status).all()
        return resp
    
    def __repr__(self):
        """String representation of the event."""
        return f"<{self.id}: {self.created}>"


class ObjectEvent(db.Model, Timestamp):
    """Event related to an Identifier or Relationship."""

    __tablename__ = 'objectevent'
    __table_args__ = (
        PrimaryKeyConstraint(
            'event_id', 'object_uuid', 'payload_type', 'payload_index',
            name='pk_objectevent'),
    )

    event_id = db.Column(UUIDType, db.ForeignKey(Event.id), nullable=False)
    object_uuid = db.Column(UUIDType, nullable=False)
    payload_type = db.Column(db.Enum(PayloadType), nullable=False)
    payload_index = db.Column(db.Integer, nullable=False)

    event = db.relationship(Event, backref='object_events')

    @property
    def object(self) -> Union[Identifier, Relationship]:
        """Get the associated Identifier or Relationship."""
        if self.payload_type == PayloadType.Identifier:
            return Identifier.query.get(self.object_uuid)
        else:
            return Relationship.query.get(self.object_uuid)

    def __repr__(self):
        """String representation of the object event."""
        return f"<{self.event_id}: {self.object_uuid}>"
