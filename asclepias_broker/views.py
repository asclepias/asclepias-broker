# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 CERN.
#
# Asclepias Broker is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

from flask import Blueprint, abort, current_app, jsonify, render_template, \
    request
from flask.views import MethodView
from invenio_rest import ContentNegotiatedMethodView
from webargs import fields, validate
from webargs.flaskparser import use_kwargs

from asclepias_broker.api import RelationshipAPI, EventAPI

from .models import Identifier

blueprint = Blueprint('asclepias_ui', __name__, template_folder='templates')

#
# UI Views
#
@blueprint.route('/list')
def listpids():
    pids = Identifier.query
    return render_template('list.html', pids=pids)


@blueprint.route('/citations/<path:pid_value>')
def citations(pid_value):
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
        return render_template('citations.html', target=target, citations=citations)


@blueprint.route('/relationships')
def relationships():
    id_ = request.values['id']
    scheme = request.values['scheme']
    relation = request.values['relation']

    identifier = Identifier.query.filter_by(scheme=scheme, value=id_).first()
    if not identifier:
        return abort(404)
    else:
        citations = RelationshipAPI.get_citations2(identifier, relation)
        return render_template('gcitations.html', target=identifier, citations=citations)


#
# REST API Views
#
api_blueprint = Blueprint('asclepias_api', __name__, url_prefix='/api')


class EventResource(MethodView):
    def post(self):
        EventAPI.handle_event(request.json)
        return "OK", 200


class RelationshipResource(ContentNegotiatedMethodView):
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
        'from_': fields.Str(load_from='from', missing=None),
        'to': fields.Str(missing=None),
        'group_by': fields.Str(
            load_from='groupBy',
            validate=validate.OneOf(['identity', 'version']),
            missing='identity'),
    })
    def get(self, id_, scheme, relation, type_, from_, to, group_by):
        # TODO: Serialize using marshmallow (.schemas.scholix)
        src_doc, relationships = RelationshipAPI.get_relationships(
            id_, scheme, relation, target_type=type_, from_=from_, to=to,
            group_by=group_by)
        if not src_doc:
            return jsonify(message='No object found with identifier "{}"'.format(id_)), 404
        source = (src_doc and src_doc.to_dict()) or {}
        return jsonify({
            'Source': source,
            'Relationship': [{'Target': t.to_dict(), 'LinkHistory': h}
                             for t, h in relationships],
            'Relation': relation,
            'GroupBy': group_by,
        })


#
# Blueprint definition
#

event_view = EventResource.as_view('event')

relationships_view = RelationshipResource.as_view('relationships')

api_blueprint.add_url('/event', view_func=event_view)
api_blueprint.add_url('/relationships', view_func=relationships_view)
