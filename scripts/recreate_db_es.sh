export SQLALCHEMY_DATABASE_URI='postgresql+psycopg2://asclepias:asclepias@localhost/asclepias'
invenio index destroy --force --yes-i-know
invenio db destroy --yes-i-know
invenio db init
invenio db create
invenio index init
