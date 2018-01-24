import sys
import json
from flask import Flask, request, abort, render_template

from asclepias_broker.broker import SoftwareBroker
from asclepias_broker.datastore import Identifier, Relationship, RelationshipType

app = Flask(__name__)
broker = SoftwareBroker()

@app.route('/')
def index():
    return "Hello"

@app.route('/receive/', methods=['POST', ])
def event_receiver():
    pass


@app.route('/load/')
def load_events():
    event_file='../examples/events.json'
    with open(event_file) as f:
        for event in json.load(f):
            broker.handle_event(event)
    return "OK"


@app.route('/list/')
def listpids():
    pids = broker.session.query(Identifier)
    return render_template('list.html', pids=pids)

@app.route('/citations/<path:pid_value>/')
def citations(pid_value):
    identifier = broker.session.query(Identifier).filter_by(
        scheme='DOI', value=pid_value).first()
    if not identifier:
        return abort(404)
    else:
        citations = broker.get_citations(identifier, with_parents=True,
            with_siblings=True, expand_target=True)
        target = citations[0]
        citations = citations[1:]
        return render_template('citations.html', target=target, citations=citations)
