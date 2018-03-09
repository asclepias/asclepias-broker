import json

from flask import Blueprint, abort, current_app, jsonify, render_template, \
    request
from webargs import fields, validate
from webargs.flaskparser import use_kwargs

from .datastore import Identifier

blueprint = Blueprint('asclepias_ui', __name__, template_folder='templates')

#
# UI Views
#
@blueprint.route('/receive', methods=['POST', ])
def event_receiver():
    current_app.broker.handle_event(request.json)
    return "OK", 200


@blueprint.route('/load')
def load_events():
    event_file = '../examples/events.json'
    with open(event_file) as f:
        for event in json.load(f):
            current_app.broker.handle_event(event)
    return "OK"


@blueprint.route('/list')
def listpids():
    pids = current_app.broker.session.query(Identifier)
    return render_template('list.html', pids=pids)


@blueprint.route('/citations/<path:pid_value>')
def citations(pid_value):
    identifier = current_app.broker.session.query(Identifier).filter_by(
        scheme='doi', value=pid_value).first()
    if not identifier:
        return abort(404)
    else:
        citations = current_app.broker.get_citations(identifier, with_parents=True,
            with_siblings=True, expand_target=True)
        target = citations[0]
        citations = citations[1:]
        return render_template('citations.html', target=target, citations=citations)


@blueprint.route('/relationships')
def relationships():
    id_ = request.values['id']
    scheme = request.values['scheme']
    relation = request.values['relation']

    broker = current_app.broker
    identifier = broker.session.query(Identifier).filter_by(
        scheme=scheme, value=id_).first()
    if not identifier:
        return abort(404)
    else:
        citations = broker.get_citations2(identifier, relation)
        return render_template('gcitations.html', target=identifier, citations=citations)


#
# REST API Views
#
api_blueprint = Blueprint('asclepias_api', __name__, url_prefix='/api')


@api_blueprint.route('/relationships')
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
def api_relationships(id_, scheme, relation, type_, from_, to, group_by):
    # TODO: Serialize using marshmallow (.schemas.scholix)
    src_doc, relationships = current_app.broker.get_relationships(
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
