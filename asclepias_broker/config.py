# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 CERN.
#
# Asclepias Broker is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Configuration for Asclepias Broker.

See also `Invenio-Config <https://invenio-config.readthedocs.io/en/latest/>`_
for more details, like e.g. how to override configuration via environment
variables or an ``invenio.cfg`` file.
"""

from __future__ import absolute_import, print_function

import os
from datetime import timedelta

from invenio_app.config import APP_DEFAULT_SECURE_HEADERS
from invenio_records_rest.facets import range_filter, terms_filter
from invenio_records_rest.utils import deny_all
from invenio_search.api import RecordsSearch
from celery.schedules import crontab

from .search.query import enum_term_filter, nested_range_filter, \
    nested_terms_filter, simple_query_string_filter


def _parse_env_bool(var_name, default=None):
    value = str(os.environ.get(var_name)).lower()
    if value in ('true', '1'):
        return True
    elif value in ('false', '0'):
        return False
    return default


# Flask configuration
# ===================
SECRET_KEY = 'CHANGE_ME'
"""
Flask's :data:`flask:SECRET_KEY`. This is an essential variable that has to be
set before deploying the broker service to a production environment. It's used
by Invenio/Flask in various places for encrypting/hashing/signing sessions,
passwords, tokens, etc. You can generate one using::

    python -c 'import os; print(os.urandom(32))'
"""

# Database
# ========
SQLALCHEMY_DATABASE_URI = \
    'postgresql+psycopg2://asclepias:asclepias@localhost/asclepias'
"""SQLAlchemy database connection string.

See also SQLAlchemy's :ref:`sqlalchemy:database_urls` docs.
"""

# Search
# ======
ELASTICSEARCH_HOST = os.environ.get('ELASTICSEARCH_HOST', 'localhost')
ELASTICSEARCH_PORT = int(os.environ.get('ELASTICSEARCH_PORT', '9200'))
ELASTICSEARCH_USER = os.environ.get('ELASTICSEARCH_USER')
ELASTICSEARCH_PASSWORD = os.environ.get('ELASTICSEARCH_PASSWORD')
ELASTICSEARCH_URL_PREFIX = os.environ.get('ELASTICSEARCH_URL_PREFIX', '')
ELASTICSEARCH_USE_SSL = _parse_env_bool('ELASTICSEARCH_USE_SSL')
ELASTICSEARCH_VERIFY_CERTS = _parse_env_bool('ELASTICSEARCH_VERIFY_CERTS')

es_host_params = {
    'host': ELASTICSEARCH_HOST,
    'port': ELASTICSEARCH_PORT,
}
if ELASTICSEARCH_USER and ELASTICSEARCH_PASSWORD:
    es_host_params['http_auth'] = (ELASTICSEARCH_USER, ELASTICSEARCH_PASSWORD)
if ELASTICSEARCH_URL_PREFIX:
    es_host_params['url_prefix'] = ELASTICSEARCH_URL_PREFIX
if ELASTICSEARCH_USE_SSL is not None:
    es_host_params['use_ssl'] = ELASTICSEARCH_USE_SSL
if ELASTICSEARCH_VERIFY_CERTS is not None:
    es_host_params['verify_certs'] = ELASTICSEARCH_VERIFY_CERTS

SEARCH_ELASTIC_HOSTS = [es_host_params]
"""Elasticsearch hosts configuration.

For a single-node cluster you can configure the connection via the following
environment variables:

* ``ELASTICSEARCH_HOST`` and ``ELASTICSEARCH_PORT``. ``localhost`` and ``9200``
  by default respectively
* ``ELASTICSEARCH_URL_PREFIX``. URL prefix for the Elasticsearch host, e.g.
  ``es`` would result in using ``http://localhost:9200/es``
* ``ELASTICSEARCH_USER`` and ``ELASTICSEARCH_PASSWORD``. Used for Basic HTTP
  authentication. By default not set
* ``ELASTICSEARCH_USE_SSL`` and ``ELASTICSEARCH_VERIFY_CERTS``

For more complex multi-node cluster setups see `Invenio-Search
<https://invenio-search.readthedocs.io/en/latest/configuration.html>`_
documentation.
"""

SEARCH_MAPPINGS = ['relationships']

# Redis
# =====
REDIS_BASE_URL = os.environ.get('REDIS_BASE_URL', 'redis://localhost:6379')
"""Redis base host URL.

Used for Celery results, rate-limiting and session storage. Can be set via the
environment variable ``REDIS_BASE_URL``.
"""

# Celery configuration
# ====================
BROKER_URL = 'amqp://guest:guest@localhost:5672/'
"""Celery broker URL.

See also `Celery's documentation
<http://docs.celeryproject.org/en/latest/userguide/configuration.html#std:setting-broker_url>`_.
"""
CELERY_BROKER_URL = BROKER_URL
CELERY_RESULT_BACKEND = f'{REDIS_BASE_URL}/2'
CELERY_BEAT_SCHEDULE = {
    'accounts': {
        'task': 'invenio_accounts.tasks.clean_session_table',
        'schedule': timedelta(minutes=60),
    },
    'reindex': {
        'task': 'asclepias_broker.search.tasks.reindex_all_relationships',
        'schedule': timedelta(hours=24)
    },
    'notify': {
        'task': 'asclepias_broker.monitoring.tasks.sendMonitoringReport',
        'schedule':  crontab(hour=0, minute=0, day_of_week=0)
    },
}

SENTRY_DSN = None
"""Sentry DSN for logging errors and warnings."""

# REST
# ====
REST_ENABLE_CORS = True
RECORDS_REST_ENDPOINTS = dict(
    relid=dict(
        pid_type='relid',
        pid_minter='relid',
        pid_fetcher='relid',
        search_class=RecordsSearch,
        indexer_class=None,
        search_index='relationships',
        search_type=None,
        search_factory_imp='asclepias_broker.search.query.search_factory',
        # Only the List GET view is available
        create_permission_factory_imp=deny_all,
        delete_permission_factory_imp=deny_all,
        update_permission_factory_imp=deny_all,
        read_permission_factory_imp=deny_all,
        links_factory_imp=lambda p, **_: None,
        record_serializers={
            'application/json': ('invenio_records_rest.serializers'
                                 ':json_v1_response'),
        },
        # TODO: Implement marshmallow serializers
        search_serializers={
            'application/json': ('invenio_records_rest.serializers'
                                 ':json_v1_search'),
        },
        list_route='/relationships',
        item_route='/relationships/<pid(relid):pid_value>',
        default_media_type='application/json',
        max_result_window=10000,
        error_handlers=dict(),
    ),
    meta=dict(
        pid_type='meta',
        pid_minter='relid',
        pid_fetcher='relid',
        search_class=RecordsSearch,
        indexer_class=None,
        search_index='relationships',
        search_type=None,
        search_factory_imp='asclepias_broker.search.query.meta_search_factory',
        # Only the List GET view is available
        create_permission_factory_imp=deny_all,
        delete_permission_factory_imp=deny_all,
        update_permission_factory_imp=deny_all,
        read_permission_factory_imp=deny_all,
        links_factory_imp=lambda p, **_: None,
        record_serializers={
            'application/json': ('invenio_records_rest.serializers'
                                 ':json_v1_response'),
        },
        # TODO: Implement marshmallow serializers
        search_serializers={
            'application/json': ('invenio_records_rest.serializers'
                                 ':json_v1_search'),
        },
        list_route='/metadata',
        item_route='/metadata/<pid(meta):pid_value>',
        default_media_type='application/json',
        max_result_window=10000,
        error_handlers=dict(),
    ),
)
RECORDS_REST_FACETS = dict(
    relationships=dict(
        aggs=dict(
            type=dict(
                terms=dict(field='Source.Type.Name')
            ),
            publication_year=dict(
                date_histogram=dict(
                    field='Source.PublicationDate',
                    interval='year',
                    format='yyyy',
                ),
            ),
        ),
        # TODO: Investigate using a webargs-powered search_factory to better
        # validate and build the query...
        filters=dict(
            id=nested_terms_filter('Target.SearchIdentifier.ID'),
            scheme=nested_terms_filter('Target.SearchIdentifier.IDScheme'),
            group_by=enum_term_filter(
                label='group_by',
                field='Grouping',
                choices={'identity': 'identity', 'version': 'version'}
            ),
            **{'from': nested_range_filter(
                'from', 'History.LinkPublicationDate', op='gte')},
            to=nested_range_filter(
                'to', 'History.LinkPublicationDate', op='lte'),
            relation=enum_term_filter(
                label='relation',
                field='RelationshipType',
                choices={
                    'isCitedBy': 'Cites',
                    'isSupplementedBy': 'IsSupplementTo',
                    'isRelatedTo': 'IsRelatedTo'
                }
            ),
            keyword=simple_query_string_filter('Source.Keywords_all'),
            journal=nested_terms_filter('Source.Publisher.Name','Source.Publisher'),
        ),
        post_filters=dict(
            type=terms_filter('Source.Type.Name'),
            publication_year=range_filter(
                'Source.PublicationDate', format='yyyy', start_date_math='/y', end_date_math='/y'),
        )
    ),
    
    # The topHits agg can't be addded here due to limitations in elasticsearch_dsl aggs function so that is added in query.py
    metadata=dict(
        aggs=dict(
            NumberOfTargets=dict(
                cardinality=dict(field='Target.ID')
            ),
            publication_year=dict(
                date_histogram=dict(
                    field='Source.PublicationDate',
                    interval='year',
                    format='yyyy',
                ),
            ),
        ),
        filters=dict(
            group_by=enum_term_filter(
                label='group_by',
                field='Grouping',
                choices={'identity': 'identity', 'version': 'version'}
            ),
            keyword=simple_query_string_filter('Source.Keywords_all'),
            journal=nested_terms_filter('Source.Publisher.Name','Source.Publisher'),
            publication_year=range_filter(
                'Source.PublicationDate', format='yyyy', start_date_math='/y', end_date_math='/y'),
        ),
    )
)
# TODO: See if this actually works
RECORDS_REST_SORT_OPTIONS = dict(
    relationships=dict(
        mostrecent=dict(
            fields=['Source.PublicationDate'],
            default_order='desc',
        ),
    ),
)
RECORDS_REST_DEFAULT_SORT = {
    'relationships': {
        'noquery': '-mostrecent'
    }
}
RATELIMIT_STORAGE_URL = f'{REDIS_BASE_URL}/3'
RATELIMIT_AUTHENTICATED_USER = '20000 per hour;500 per minute'

APP_DEFAULT_SECURE_HEADERS['force_https'] = True
APP_DEFAULT_SECURE_HEADERS['session_cookie_secure'] = True

# Application
# ===========
#: Determines if the search index will be updated after ingesting an event
ASCLEPIAS_SEARCH_INDEXING_ENABLED = False

# JSONSchemas
# ===========
JSONSCHEMAS_HOST = 'https://schemas.asclepias.github.io'

# Accounts
# ========
ACCOUNTS = False
ACCOUNTS_SESSION_REDIS_URL = f'{REDIS_BASE_URL}/1'
ACCOUNTS_REGISTER_BLUEPRINT = False

SECURITY_REGISTERABLE = False
SECURITY_RECOVERABLE = False
SECURITY_CONFIRMABLE = False
SECURITY_CHANGEABLE = False

# Theme configuration
# ===================
THEME_SITENAME = 'Asclepias Broker'
THEME_FRONTPAGE = False

# Email configuration
# ===================
MAIL_SUPPRESS_SEND = True

# Logging
# =======
LOGGING_SENTRY_CELERY = True
