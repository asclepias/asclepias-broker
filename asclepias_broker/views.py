# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 CERN.
#
# Asclepias Broker is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
"""Views for receiving and querying events and relationships."""
import json

from flask import Blueprint, abort, request
from flask.views import MethodView
from flask_login import current_user
from invenio_oauth2server import require_api_auth
from jsonschema.exceptions import ValidationError as JSONValidationError
from marshmallow.exceptions import \
    ValidationError as MarshmallowValidationError

from asclepias_broker.api import EventAPI, RelationshipAPI

from .errors import PayloadValidationRESTError
from .models import Identifier

# TODO: we need this blueprint in order to run
# asclepias_broker.tasks.process_event
blueprint = Blueprint('asclepias_ui', __name__, template_folder='templates')


@blueprint.route('/ping')
def ping():
    """Load balancer ping view."""
    return 'OK'


#
# REST API Views
#
api_blueprint = Blueprint('asclepias_api', __name__)


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


@api_blueprint.route('/citations/<path:pid_value>')
@require_api_auth()
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

        return json.dumps({'target': _target_to_json(target),
                           'citations': _citations_to_json(citations)})


def _citations_to_json(citations):
    citations_json = []
    for c in citations:
        ids, rels = c
        PIDs = []
        for id in ids:
            PIDs.append(id.value)
        citing_relations = []
        for rel in rels:
            citing_relations.append(str(rel))
        citations_json.append({'PIDs': PIDs,
                               'citingRelations': citing_relations})
    return citations_json


def _target_to_json(target):
    t_ids, t_rels = target
    equivalent_PIDs = []
    for id in t_ids:
        equivalent_PIDs.append(id.value)
    equivalence_relations = []
    for rel in t_rels:
        equivalence_relations.append(str(rel)),
    target_json = {
        'equivalentPIDs': equivalent_PIDs,
        'equivalenceRelations': equivalence_relations
    }
    return target_json


@api_blueprint.route('/db-relationships')
@require_api_auth()
def relationships():
    """Renders relationships for an identifiers from DB."""
    id_ = request.values['id']
    scheme = request.values['scheme']
    relation = request.values['relation']
    grouping = request.values.get('grouping')  # optional parameter

    identifier = Identifier.query.filter_by(scheme=scheme, value=id_).first()
    if not identifier:
        return abort(404)
    else:
        if grouping:
            citations = RelationshipAPI\
                .get_citations2(identifier, relation, grouping)
        else:
            citations = RelationshipAPI.get_citations2(identifier, relation)

        citations_ids = []
        for gid, citlist in citations:
            for grouprel, group, id in citlist:
                citations_ids.append(id.value)

        return json.dumps({'target': identifier.value,
                           'citations': citations_ids})


#
# Blueprint definition
#

event_view = EventResource.as_view('event')

api_blueprint.add_url_rule('/event', view_func=event_view)
