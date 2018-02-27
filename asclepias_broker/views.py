import json
from flask import current_app, Blueprint, abort, render_template, request
from .datastore import Identifier
blueprint = Blueprint(
    'asclepias',
    __name__,
    url_prefix='/',
    template_folder='templates',
    #static_folder='static',
)

@blueprint.route('')
def index():
    return "<body>Hello</body>"

@blueprint.route('receive', methods=['POST', ])
def event_receiver():
    current_app.broker.handle_event(request.json)
    return "OK", 200


@blueprint.route('load')
def load_events():
    event_file='../examples/events.json'
    with open(event_file) as f:
        for event in json.load(f):
            current_app.broker.handle_event(event)
    return "OK"


@blueprint.route('list')
def listpids():
    pids = current_app.broker.session.query(Identifier)
    return render_template('list.html', pids=pids)


@blueprint.route('citations/<path:pid_value>')
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


@blueprint.route('relationships')
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
