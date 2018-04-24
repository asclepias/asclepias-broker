# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 CERN.
#
# Asclepias Broker is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Default configuration for Asclepias Broker."""

from __future__ import absolute_import, print_function

from datetime import timedelta

from invenio_app.config import APP_DEFAULT_SECURE_HEADERS
from invenio_records_rest.facets import terms_filter
from invenio_records_rest.utils import deny_all
from invenio_search.api import RecordsSearch

from asclepias_broker.search import enum_term_filter, nested_range_filter, \
    nested_terms_filter


def _(x):
    """Identity function used to trigger string extraction."""
    return x


# Rate limiting
# =============

RATELIMIT_STORAGE_URL = 'redis://localhost:6379/3'

# I18N
# ====
#: Default language
BABEL_DEFAULT_LANGUAGE = 'en'
#: Default time zone
BABEL_DEFAULT_TIMEZONE = 'Europe/Zurich'


# Base templates
# ==============
#: Global base template.
BASE_TEMPLATE = 'invenio_theme/page.html'
#: Cover page base template (used for e.g. login/sign-up).
COVER_TEMPLATE = 'invenio_theme/page_cover.html'
#: Footer base template.
FOOTER_TEMPLATE = 'invenio_theme/footer.html'
#: Header base template.
HEADER_TEMPLATE = 'invenio_theme/header.html'
#: Settings base template.
SETTINGS_TEMPLATE = 'invenio_theme/page_settings.html'


# Theme configuration
# ===================
#: Site name
THEME_SITENAME = _('Asclepias Broker')
#: Use default frontpage.
THEME_FRONTPAGE = False


# Email configuration
# ===================
#: Email address for support.
SUPPORT_EMAIL = "info@inveniosoftware.org"
#: Disable email sending by default.
MAIL_SUPPRESS_SEND = True

# Assets
# ======
#: Static files collection method (defaults to copying files).
COLLECT_STORAGE = 'flask_collect.storage.file'

# Accounts
# ========
SECURITY_EMAIL_SENDER = SUPPORT_EMAIL
SECURITY_EMAIL_SUBJECT_REGISTER = _(
    "Welcome to Asclepias Broker!")
ACCOUNTS_SESSION_REDIS_URL = 'redis://localhost:6379/1'

SECURITY_REGISTERABLE = False
SECURITY_RECOVERABLE = False
SECURITY_CONFIRMABLE = False
SECURITY_CHANGEABLE = False

# Celery configuration
# ====================
BROKER_URL = 'amqp://guest:guest@mq:5672/'
CELERY_BROKER_URL = 'amqp://guest:guest@localhost:5672/'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/2'

#: Scheduled tasks configuration (aka cronjobs).
CELERY_BEAT_SCHEDULE = {
    'indexer': {
        'task': 'invenio_indexer.tasks.process_bulk_queue',
        'schedule': timedelta(minutes=5),
    },
    'accounts': {
        'task': 'invenio_accounts.tasks.clean_session_table',
        'schedule': timedelta(minutes=60),
    },
}

# Database
# ========

SQLALCHEMY_DATABASE_URI = \
    'postgresql+psycopg2://asclepias:asclepias@localhost/asclepias'


# Search
# ======

SEARCH_MAPPINGS = ['relationships']


# JSONSchemas
# ===========

JSONSCHEMAS_HOST = 'asclepias-broker.com'

# Flask configuration
# ===================
# See details on
# http://flask.pocoo.org/docs/0.12/config/#builtin-configuration-values

SECRET_KEY = 'CHANGE_ME'

#: Max upload size for form data via application/mulitpart-formdata
MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100 MiB

# REST
# ====
#: Enable Cross-Origin Resource Sharing support.
REST_ENABLE_CORS = True

RECORDS_REST_ENDPOINTS = dict(
    relid=dict(
        pid_type='relid',
        pid_minter='relid',
        pid_fetcher='relid',
        # TODO: Make our own search class
        search_class=RecordsSearch,
        indexer_class=None,
        search_index='relationships',
        search_type=None,
        search_factory_imp='asclepias_broker.search.search_factory',
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
)


RECORDS_REST_FACETS = dict(
    relationships=dict(
        aggs=dict(
            type=dict(
                terms=dict(field='Source.Type.Name')
            ),
        ),
        # TODO: Investigate using a webargs-powered search_factory to better
        # validate and build the query...
        filters=dict(
            id=nested_terms_filter('Target.Identifier.ID'),
            scheme=nested_terms_filter('Target.Identifier.IDScheme'),
            groupBy=enum_term_filter(
                label='groupBy',
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
            type=terms_filter('Source.Type.Name'),
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
        'noquery': 'mostrecent'
    }
}

APP_DEFAULT_SECURE_HEADERS['force_https'] = True
APP_DEFAULT_SECURE_HEADERS['session_cookie_secure'] = True

# Debug
# =====
# Flask-DebugToolbar is by default enabled when the application is running in
# debug mode. More configuration options are available at
# https://flask-debugtoolbar.readthedocs.io/en/latest/#configuration

#: Switches off incept of redirects by Flask-DebugToolbar.
DEBUG_TB_INTERCEPT_REDIRECTS = False
