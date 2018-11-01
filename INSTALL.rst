..
    Copyright (C) 2018 CERN.

    Asclepias Broker is free software; you can redistribute it and/or modify it
    under the terms of the MIT License; see LICENSE file for more details.

Installation
============

First you need to install `pipenv
<https://docs.pipenv.org/install/#installing-pipenv>`_, it will handle the
virtual environment creation for the project in order to sandbox our Python
environment, as well as manage the dependencies installation, among other
things.

For running dependent services, you'll need `Docker
<https://docs.docker.com/install/>`_ (``>=18.06.1``) and `Docker Compose
<https://docs.docker.com/compose/install/>`_ (``>=1.22.0``), in order get
things up and running quickly but also to make sure that the same versions and
configuration for these services is used, independent of your OS.

Start all the dependent services using ``docker-compose`` (this will start
PostgreSQL, Elasticsearch 6, RabbitMQ, Redis, Kibana and Flower):

.. code-block:: shell

    $ docker-compose up -d

.. note::

    Make sure you have `enough virtual memory
    <https://www.elastic.co/guide/en/elasticsearch/reference/current/docker.html#docker-cli-run-prod-mode>`_
    for Elasticsearch in Docker:

    .. code-block:: shell

        # Linux
        $ sysctl -w vm.max_map_count=262144

        # macOS
        $ screen ~/Library/Containers/com.docker.docker/Data/com.docker.driver.amd64-linux/tty
        <enter>
        linut00001:~# sysctl -w vm.max_map_count=262144

Next, bootstrap the instance (this will install all Python dependencies):

.. code-block:: shell

    $ ./scripts/bootstrap

Next, create the database tables and search indices:

.. code-block:: shell

    $ ./scripts/setup

Running
-------
Start the webserver and the celery worker:

.. code-block:: shell

    $ ./scripts/server

Start a Python shell:

.. code-block:: shell

    $ ./scripts/console

Upgrading
---------
In order to upgrade an existing instance simply run:

.. code-block:: shell

    $ ./scripts/update

Testing
-------
Run the test suite via the provided script:

.. code-block:: shell

    $ ./run-tests.sh

Documentation
-------------
You can build the documentation with:

.. code-block:: shell

    $ pipenv run build_sphinx

Production environment
----------------------

You can simulate a full production environment using the
``docker-compose.full.yml``. You can start it like this:

.. code-block:: shell

    $ docker-compose -f docker-compose.full.yml up -d

In addition to the normal ``docker-compose.yml``, this one will start:

- HAProxy (load balancer)
- Nginx (web frontend)
- uWSGI (application container)
- Celery (background task worker)

As done for local development, you will also have to run the initial setup
script inside the running container:

.. code-block:: shell

    $ docker-compose -f docker-compose.full.yml run --rm web ./scripts/setup
