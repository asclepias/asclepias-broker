import sys
import json
from flask import Flask, request, abort, render_template, current_app
from sqltap.wsgi import SQLTapMiddleware
from flask_debugtoolbar import DebugToolbarExtension

from asclepias_broker.broker import SoftwareBroker
from asclepias_broker.datastore import Identifier, Relationship, Relation
from asclepias_broker.views import blueprint

app = Flask(__name__)
app.wsgi_app = SQLTapMiddleware(app.wsgi_app)
app.register_blueprint(blueprint)
app.config["SECRET_KEY"] = "CHANGEME"

app.debug=True
toolbar = DebugToolbarExtension(app)

engine_url = 'postgresql://admin:postgres@localhost:5432/asclepias'
# engine_url = None
# engine_url = 'postgresql://admin:postgres@localhost:5432/asclepias2'

# recreate = True
recreate = False
if recreate:
    from sqlalchemy_utils import drop_database, create_database, database_exists
    if database_exists(engine_url):
        drop_database(engine_url)
    create_database(engine_url)


broker = SoftwareBroker(db_uri=engine_url)
app.broker = broker

# @app.route('/')
# def index():
#     return "Hello"
# 
# @app.route('/receive/', methods=['POST', ])
# def event_receiver():
#     app.broker.handle_event(request.json)
#     return "OK", 200
# 
# 
# @app.route('/load/')
# def load_events():
#     event_file='../examples/events.json'
#     with open(event_file) as f:
#         for event in json.load(f):
#             broker.handle_event(event)
#     return "OK"
# 
# 
# @app.route('/list/')
# def listpids():
#     pids = broker.session.query(Identifier)
#     return render_template('list.html', pids=pids)
# 
# 
# @app.route('/citations/<path:pid_value>/')
# def citations(pid_value):
#     identifier = broker.session.query(Identifier).filter_by(
#         scheme='doi', value=pid_value).first()
#     if not identifier:
#         return abort(404)
#     else:
#         citations = broker.get_citations(identifier, with_parents=True,
#             with_siblings=True, expand_target=True)
#         target = citations[0]
#         citations = citations[1:]
#         return render_template('citations.html', target=target, citations=citations)
