
# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 CERN.
#
# Asclepias Broker is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
"""Graph database models."""

import uuid

from invenio_db import db
from sqlalchemy_utils.models import Timestamp
from sqlalchemy_utils.types import UUIDType

class ErrorMonitoring(db.Model, Timestamp):
    """Error monitoring model."""

    __tablename__ = 'error_monitoring'

    id = db.Column(UUIDType, default=uuid.uuid4, primary_key=True)
    origin = db.Column(db.String, nullable=False)
    error = db.Column(db.String)
    payload = db.Column(db.String)

    def __repr__(self):
        """String representation of the error."""
        return f"<{self.id}: {self.type.name}>"