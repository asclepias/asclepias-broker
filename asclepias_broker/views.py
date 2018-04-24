# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 CERN.
#
# Asclepias Broker is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
"""Views for receiving and querying events and relationships."""

from flask import Blueprint, abort, render_template, request
from flask.views import MethodView
from invenio_rest.errors import RESTException
from jsonschema.exceptions import ValidationError as JSONValidationError
from marshmallow.exceptions import \
    ValidationError as MarshmallowValidationError

from asclepias_broker.api import EventAPI, RelationshipAPI

from .errors import PayloadValidationRESTError
from .models import Identifier

blueprint = Blueprint('asclepias_ui', __name__, template_folder='templates')


#
# UI Views
#
@blueprint.route('/list')
def listpids():
    """Renders all identifiers in the system."""
    pids = Identifier.query
    return render_template('list.html', pids=pids)


@blueprint.route('/citations/<path:pid_value>')
def citations(pid_value):
    """Renders all citations for an identifier."""
    identifier = Identifier.query.filter_by(
        scheme='doi', value=pid_value).first()
    if not identifier:
        return abort(404)
    else:
        citations = RelationshipAPI.get_citations(
            identifier, with_parents=True, with_siblings=True,
            expand_target=True)
        target = citations[0]
        citations = citations[1:]
        return render_template(
            'citations.html', target=target, citations=citations)


@blueprint.route('/relationships')
def relationships():
    """Renders relationships for an identifiers from DB."""
    id_ = request.values['id']
    scheme = request.values['scheme']
    relation = request.values['relation']

    identifier = Identifier.query.filter_by(scheme=scheme, value=id_).first()
    if not identifier:
        return abort(404)
    else:
        citations = RelationshipAPI.get_citations2(identifier, relation)
        return render_template(
            'gcitations.html', target=identifier, citations=citations)


#
# REST API Views
#
api_blueprint = Blueprint('asclepias_api', __name__)


class EventResource(MethodView):
    """Event resource."""

    def post(self):
        """Submit an event."""
        try:
            EventAPI.handle_event(request.json)
        except JSONValidationError as e:
            raise PayloadValidationRESTError(e.message, code=422)
        except MarshmallowValidationError as e:
            msg = "Validation error: " + str(e.messages)
            raise PayloadValidationRESTError(msg, code=422)
        return "Accepted", 202


#
# Blueprint definition
#

event_view = EventResource.as_view('event')

api_blueprint.add_url_rule('/event', view_func=event_view)
