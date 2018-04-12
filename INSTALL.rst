..
    Copyright (C) 2018 CERN.

    Asclepias Broker is free software; you can redistribute it and/or modify it
    under the terms of the MIT License; see LICENSE file for more details.

Installation
============

To run an instance of ``Asclepias Broker`` you will need a PostgreSQL and Elasticsearch, which can be installed directly on your machine,
or you can use ``docker-compose`` with the provided docker configuration to run those in the sandboxed docker environment (recommended).

Quick start
-----------

.. note::

    The docker configuration provided in this module uses PostgresSQL and ElasticSearch 6.

Install ``docker`` and ``docker-compose`` in your machine.
Then, create and run the services using the docker containers:

.. code-block:: console

    $ cd asclepias-broker
    $ docker-compose up db es kibana

Database and search index
-------------------------
The last you need to do is to create the database tables and search indexes.
Connect to the web container:

.. code-block:: console

    $ docker run -it asclepias-broker-web-ui /bin/bash

Run the following commands inside the docker container.
Create the database and tables:

.. code-block:: console

   $ asclepias-broker db init create

Create the search indexes and indexing queue:

.. code-block:: console

    $ asclepias-broker index init
    $ asclepias-broker index queue init

Open your browser and visit the url https://localhost.

.. note::

    If for some reason something failed during table or index creation, you
    can remove everything again with:

    .. code-block:: console

        $ asclepias-broker db drop --yes-i-know
        $ asclepias-broker index destroy --force

Development setup
-----------------

The recommended way of development is to install and run the web app locally in your machine, while keeping
the other services (provided by `docker-compose.yml`) on Docker containers.
See the `Developer Guide <https://http://invenio.readthedocs.io/en/latest/developersguide/>` documentation.
