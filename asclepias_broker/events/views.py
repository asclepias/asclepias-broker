# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 CERN.
#
# Asclepias Broker is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
"""Event views."""
from flask import Blueprint, request
from flask.views import MethodView
from flask_login import current_user
from invenio_oauth2server import require_api_auth
from jsonschema.exceptions import ValidationError as JSONValidationError
from marshmallow.exceptions import \
    ValidationError as MarshmallowValidationError

from asclepias_broker.events.api import EventAPI

from .errors import PayloadValidationRESTError

#
# REST API Views
#
blueprint = Blueprint('asclepias_events', __name__)


class EventResource(MethodView):
    """Event resource."""

    @require_api_auth()
    def post(self):
        """Submit an event."""
        try:
            no_index = bool(request.args.get('noindex', False))
            EventAPI.handle_event(request.json, user_id=current_user.id,
                                  no_index=no_index)
        except JSONValidationError as e:
            raise PayloadValidationRESTError(e.message, code=422)
        except MarshmallowValidationError as e:
            msg = "Validation error: " + str(e.messages)
            raise PayloadValidationRESTError(msg, code=422)
        return "Accepted", 202


blueprint.add_url_rule('/event', view_func=EventResource.as_view('event'))
