# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 CERN.
#
# Asclepias Broker is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
"""Views for receiving and querying events and relationships."""

from flask import Blueprint, abort, jsonify, render_template, request, url_for
from flask.views import MethodView
from invenio_rest import ContentNegotiatedMethodView
from invenio_rest.errors import FieldError, RESTException, RESTValidationError
from jsonschema.exceptions import ValidationError as JSONValidationError
from marshmallow.exceptions import \
    ValidationError as MarshmallowValidationError
from webargs import fields, validate
from webargs.flaskparser import parser, use_kwargs

from asclepias_broker.api import EventAPI, RelationshipAPI

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


class ObjectNotFoundRESTError(RESTException):
    """Object not found error."""

    code = 404

    def __init__(self, identifier, **kwargs):
        """Initialize the ObjectNotFound REST exception."""
        super(ObjectNotFoundRESTError, self).__init__(**kwargs)
        self.description = \
            'No object found with identifier [{}]'.format(identifier)


class PayloadValidationRESTError(RESTException):
    """Invalid payload error."""

    code = 400

    def __init__(self, error_message, code=None, **kwargs):
        """Initialize the PayloadValidation REST exception."""
        if code:
            self.code = code
        super(PayloadValidationRESTError, self).__init__(**kwargs)
        self.description = error_message


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


class RelationshipResource(ContentNegotiatedMethodView):
    """Relationship resource."""

    @use_kwargs({
        'id_': fields.Str(load_from='id', required=True),
        'scheme': fields.Str(missing='doi'),
        'relation': fields.Str(
            required=True,
            validate=validate.OneOf([
                'isCitedBy', 'cites', 'isSupplementTo', 'isSupplementedBy',
            ])
        ),
        # TODO: Convert to datetime...
        'type_': fields.Str(load_from='type', missing=None),
        'from_': fields.DateTime(load_from='from', missing=None),
        'to': fields.DateTime(missing=None),
        'group_by': fields.Str(
            load_from='groupBy',
            validate=validate.OneOf(['identity', 'version']),
            missing='identity'),
    })
    def get(self, id_, scheme, relation, type_, from_, to, group_by):
        """Query relationships."""
        # TODO: Serialize using marshmallow (.schemas.scholix). This involves
        # passing `serializers` for the superclass' constructor.
        page = request.values.get('page', 1, type=int)
        size = request.values.get('size', 10, type=int)
        src_doc, relationships = RelationshipAPI.get_relationships(
            id_, scheme, relation, target_type=type_, from_=from_, to=to,
            group_by=group_by, page=page, size=size)
        if not src_doc:
            raise ObjectNotFoundRESTError(id_)
        source = (src_doc and src_doc.to_dict()) or {}

        urlkwargs = {
            '_external': True,
            'size': size, 'id': id_, 'scheme': scheme, 'relation': relation,
        }
        if type_:
            urlkwargs['type'] = type_
        if from_:
            urlkwargs['from'] = from_
        if to:
            urlkwargs['to'] = to
        if group_by:
            urlkwargs['groupBy'] = group_by

        endpoint = '.relationships'
        links = {'self': url_for(endpoint, page=page, **urlkwargs)}
        if page > 1:
            links['prev'] = url_for(endpoint, page=page - 1, **urlkwargs)
        # TODO: add max_window_size in config
        MAX_WINDOW_SIZE = 10000
        if size * page < relationships['total'] and \
                size * page < MAX_WINDOW_SIZE:
            links['next'] = url_for(endpoint, page=page + 1, **urlkwargs)
        return jsonify({
            'Source': source,
            'Relationship': relationships['hits'],
            'Relation': relation,
            'GroupBy': group_by,
            'Links': links,
            'Total': relationships['total'],
        })


@parser.error_handler
def validation_error_handler(error):
    """Handle and serialize errors from webargs validation."""
    raise RESTValidationError(
        errors=[FieldError(k, v) for k, v in error.messages.items()],
    )


#
# Blueprint definition
#

event_view = EventResource.as_view('event')

relationships_view = RelationshipResource.as_view('relationships')

api_blueprint.add_url_rule('/event', view_func=event_view)
api_blueprint.add_url_rule('/relationships', view_func=relationships_view)
