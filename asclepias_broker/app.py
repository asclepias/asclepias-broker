import os
from flask import Flask
from flask_debugtoolbar import DebugToolbarExtension
from sqlalchemy_utils import create_database, database_exists, drop_database
from sqltap.wsgi import SQLTapMiddleware

from asclepias_broker.broker import SoftwareBroker
from asclepias_broker.views import blueprint, api_blueprint


def create_app(config=None):
    app = Flask(__name__)
    app.register_blueprint(blueprint)
    app.register_blueprint(api_blueprint)
    app.config["SECRET_KEY"] = "CHANGEME"

    if app.debug:
        app.wsgi_app = SQLTapMiddleware(app.wsgi_app)
        DebugToolbarExtension(app)

    db_uri = os.environ.get(
        'SQLALCHEMY_DATABASE_URI',
        'postgresql://admin:postgres@localhost:5432/asclepias')

    # recreate = True
    recreate = False
    if recreate:
        if database_exists(db_uri):
            drop_database(db_uri)
        create_database(db_uri)

    app.broker = SoftwareBroker(db_uri=db_uri)
    return app
