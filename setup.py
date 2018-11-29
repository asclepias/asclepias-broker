# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 CERN.
# Copyright (c) 2017 Thomas P. Robitaille.
#
# Asclepias Broker is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Scholarly link broker for the Asclepias project."""

import os

from setuptools import find_packages, setup

readme = open('README.rst').read()

packages = find_packages()

# Get the version string. Cannot be done with import!
g = {}
with open(os.path.join('asclepias_broker', 'version.py'), 'rt') as fp:
    exec(fp.read(), g)
    version = g['__version__']

setup(
    name='asclepias-broker',
    version=version,
    description=__doc__,
    long_description=readme,
    keywords='scholarly link broker',
    license='MIT',
    author='CERN, Thomas Robitaille',
    author_email='info@inveniosoftware.org',
    url='https://github.com/asclepias/asclepias-broker',
    packages=packages,
    zip_safe=False,
    include_package_data=True,
    platforms='any',
    entry_points={
        'console_scripts': [
            'asclepias-broker = invenio_app.cli:cli',
        ],
        'flask.commands': [
            'metadata = asclepias_broker.metadata.cli:metadata',
            'events = asclepias_broker.events.cli:events',
            'search = asclepias_broker.search.cli:search',
            'harvester = asclepias_broker.harvester.cli:harvester',
        ],
        'invenio_config.module': [
            'asclepias_broker = asclepias_broker.config',
        ],
        'invenio_base.apps': [
            'flask_breadcrumbs = flask_breadcrumbs:Breadcrumbs',
            ('asclepias_harvester = '
             'asclepias_broker.harvester.ext:AsclepiasHarvester'),
        ],
        'invenio_base.api_apps': [
            # TODO: Fix this in Flask-Menu/Breadcrumbs (i.e. make it possible
            # to skip menus/breadcrumbs registration if the extensions aare not
            # loaded/enabled...)
            'flask_breadcrumbs = flask_breadcrumbs:Breadcrumbs',
            ('asclepias_harvester = '
             'asclepias_broker.harvester.ext:AsclepiasHarvester'),
        ],
        'invenio_base.api_blueprints': [
            'asclepias_broker = asclepias_broker.views:blueprint',
            ('asclepias_broker_events = '
             'asclepias_broker.events.views:blueprint'),
            ('asclepias_broker_search = '
             'asclepias_broker.search.views:blueprint'),
        ],
        'invenio_base.blueprints': [
            'asclepias_broker = asclepias_broker.views:blueprint',
        ],
        'invenio_celery.tasks': [
            'asclepias_broker_graph_tasks = asclepias_broker.graph.tasks',
            'asclepias_broker_search_tasks = asclepias_broker.search.tasks',
            'asclepias_harvester_tasks = asclepias_broker.harvester.tasks',
        ],
        'invenio_db.models': [
            'asclepias_broker_core = asclepias_broker.core.models',
            'asclepias_broker_events = asclepias_broker.events.models',
            'asclepias_broker_graph = asclepias_broker.graph.models',
            'asclepias_broker_metadata = asclepias_broker.metadata.models',
        ],
        'invenio_pidstore.fetchers': [
            'relid = asclepias_broker.pidstore:relid_fetcher',
        ],
        'invenio_pidstore.minters': [
            'relid = asclepias_broker.pidstore:relid_minter',
        ],
        'invenio_search.mappings': [
            'relationships = asclepias_broker.mappings',
        ],
    },
    classifiers=[
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Development Status :: 3 - Alpha',
    ],
)
