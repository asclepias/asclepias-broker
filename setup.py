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

DATABASE = "postgresql"
ELASTICSEARCH = "elasticsearch5"
INVENIO_EXTRAS = 'base,auth,{db},{es}'.format(db=DATABASE, es=ELASTICSEARCH)

tests_require = [
    'check-manifest>=0.35',
    'coverage>=4.4.1',
    'isort>=4.3',
    'mock>=2.0.0',
    'pydocstyle>=2.0.0',
    'pytest-cov>=2.5.1',
    'pytest-invenio>=1.0.1,<1.1.0',
    'pytest-mock>=1.6.0',
    'pytest-pep8>=1.0.6',
    'pytest-random-order>=0.5.4',
    'pytest>=3.3.1',
]

extras_require = {
    'docs': [
        'Sphinx>=1.5.1',
    ],
    'tests': tests_require,
}

extras_require['all'] = []
for reqs in extras_require.values():
    extras_require['all'].extend(reqs)

setup_requires = [
    'pytest-runner>=3.0.0,<5',
]

install_requires = [
    'arrow>=0.12.1',
    'Flask-Debugtoolbar>=0.10.1',
    'idutils>=1.0.0',
    'invenio-records-rest>=1.0.1',
    'invenio[{extras}]==3.0.0rc1'.format(extras=INVENIO_EXTRAS),
    'jsonschema>=2.6.0',  # TODO: Investigate `invenio-jsonschemas` usage
    'marshmallow>=2.15.0',
    'uWSGI>=2.0.17',
    'uwsgi-tools>=1.1.1',
    'uwsgitop>=0.10',
    'webargs>=2.1.0',
]

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
        'invenio_config.module': [
            'asclepias_broker = asclepias_broker.config',
        ],
        'invenio_base.api_blueprints': [
            'asclepias_broker = asclepias_broker.views:api_blueprint',
        ],
        'invenio_admin.views': [
            'asclepias_broker_identifier = '
            'asclepias_broker.admin:identifier_adminview',
            'asclepias_broker_relationship = '
            'asclepias_broker.admin:relationship_adminview',
            'asclepias_broker_event = '
            'asclepias_broker.admin:event_adminview',
        ],
        'invenio_base.blueprints': [
            'asclepias_broker = asclepias_broker.views:blueprint',
        ],
        'invenio_celery.tasks': [
            'asclepias_broker_tasks = asclepias_broker.tasks',
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
    extras_require=extras_require,
    install_requires=install_requires,
    setup_requires=setup_requires,
    tests_require=tests_require,
    classifiers=[
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Development Status :: 3 - Alpha',
    ],
)
