
# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 CERN.
#
# Asclepias Broker is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
"""Monitoring database models."""

import uuid
import enum
import datetime

from sqlalchemy.sql.sqltypes import Boolean
from sqlalchemy import func
from invenio_db import db
from sqlalchemy.dialects import postgresql
from sqlalchemy_utils.models import Timestamp
from sqlalchemy_utils.types import JSONType, UUIDType

class HarvestStatus(enum.Enum):
    """Event status."""
    New = 1
    Processing = 2
    Error = 3
    Done = 4

class ErrorMonitoring(db.Model, Timestamp):
    """Error monitoring model."""

    __tablename__ = 'error_monitoring'

    id = db.Column(UUIDType, default=uuid.uuid4, primary_key=True)
    origin = db.Column(db.String, nullable=False)
    error = db.Column(db.String)
    n_retries = db.Column(db.Integer)
    payload = db.Column(
        db.JSON()
        .with_variant(postgresql.JSONB(none_as_null=True), 'postgresql')
        .with_variant(JSONType(), 'sqlite'),
        default=dict,
    )

    @classmethod
    def getLastWeeksErrors(cls, **kwargs):
        """Gets all the errors from last week where it has been rerun for at least 2 times all ready"""
        last_week = datetime.datetime.now() - datetime.timedelta(days = 7)
        resp = cls.query.filter(cls.created > str(last_week), cls.n_retries > 2).all()
        return resp
    
    def to_dict(self):
        """Dictionary representation of the error."""
        return dict(created=self.created, updated = self.updated, id = self.id, origin = self.origin, error = self.error, payload = self.payload)


    def __repr__(self):
        """String representation of the error."""
        return str(self.to_dict())


class HarvestMonitoring(db.Model, Timestamp):
    """Harvesting monitoring model."""

    __tablename__ = 'harvest_monitoring'

    id = db.Column(UUIDType, default=uuid.uuid4, primary_key=True)
    identifier = db.Column(db.String, nullable=False)
    scheme = db.Column(db.String)
    harvester = db.Column(db.String)
    status = db.Column(db.Enum(HarvestStatus), nullable=False)

    @classmethod
    def get(cls, id: str = None, **kwargs):
        """Get the event from the database."""
        return cls.query.filter_by(id=id).one_or_none()
    
    @classmethod
    def isRecentlyAdded(cls, identifier: str, scheme: str, harvester: str, **kwargs) -> Boolean:
        """Check if the same identifier has been queried for during the last week to avoid duplicates"""
        last_week = datetime.datetime.now() - datetime.timedelta(days = 7)
        resp = cls.query.filter(cls.identifier==identifier, cls.scheme==scheme, cls.harvester==harvester, cls.updated > str(last_week)).first()
        return resp is not None

    @classmethod
    def getStatsFromLastWeek(cls):
        """Gets the stats from the last 7 days"""
        last_week = datetime.datetime.now() - datetime.timedelta(days = 7)
        resp = db.session.query(cls.status, func.count('*')).filter(cls.updated > str(last_week)).group_by(cls.status).all()
        return resp
    
    def __repr__(self):
        """String representation of the event."""
        return f"<{self.id}: {self.created} : {self.identifier}>"