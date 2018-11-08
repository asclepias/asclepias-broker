..
    Copyright (C) 2018 CERN.

    Asclepias Broker is free software; you can redistribute it and/or modify it
    under the terms of the MIT License; see LICENSE file for more details.

Usage
=====

Once you have completed the :doc:`installation` you can start interacting with
the broker. You should have already run the ``./scripts/server`` script in a
separate terminal, in order to have a view of what is happening in the web and
worker application logs while we execute various commands.

Loading data
------------

By default the broker is initialized without having any link data stored. There
are two ways to import data at the moment:

* The ``asclepias-broker events load`` CLI command
* The ``/events`` REST API endpoint

Both methods accept JSON data based on the Scholix schema. In the root
directory of this repository there is an ``examples`` folder that contains JSON
files that we will use ot import data. Specifically we will use the
``examples/cornerpy-*.json`` files, which contain link data related to the
various versions and papers of the `corner.py <https://corner.readthedocs.io>`_
astrophysics software package.

Loading events from the CLI
~~~~~~~~~~~~~~~~~~~~~~~~~~~

To load some of the events via the CLI you can run the following command:

.. code-block:: shell

    $ pipenv run asclepias-broker events load examples/cornerpy-1.json

You should then see in the terminal that your web and celery applications are
running, some messages being logged. What happened is that:

1. The CLI command loads the JSON file,
2. creates an :class:`~asclepias_broker.events.models.Event` object, and
3. sends it to be processed via the
   :func:`~asclepias_broker.graph.tasks.process_event` Celery task.
4. The task:
    a. stores the low-level information about the events (i.e.
       :class:`~asclepias_broker.core.models.Identifier` and
       :class:`~asclepias_broker.core.models.Relationship` objects),
    b. forms :class:`Groups <asclepias_broker.graph.models.Group>` based on
       their ``IsIdenticalTo`` and ``hasVersion`` relations and
    c. connects them using
       :class:`GroupRelationships <asclepias_broker.graph.models.GroupRelationship>`
       to form a graph.
    d. It then indexes these relationships, objects and their metadata in
       Elasticsearch in order to make them searchable through the REST API.

Submitting events through the REST API
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To use the REST API you will first have to create a user.

.. code-block:: shell

    # Create admin role to restrict access
    $ pipenv run asclepias-broker roles create admin
    $ pipenv run asclepias-broker access allow superuser-access role admin
    $ pipenv run asclepias-broker users create admin@cern.ch -a --password=123456
    $ pipenv run asclepias-broker roles add admin@cern.ch admin

Requests to the ``/events`` endpoint require authentication. The standard way
to authenticate is via using OAuth tokens, which can be generated through the
``asclepias-broker tokens create`` CLI command:

.. code-block:: shell

    # We store the token in the "API_TOKEN" variable for future use
    $ API_TOKEN=$(pipenv run asclepias-broker tokens create \
        --name api-token \
        --user admin@cern.ch \
        --internal)
    $ echo $API_TOKEN
    ...<generated access token>...

Now that we have our token, we can submit events via ``curl`` (or any HTTP
client of your preference):

.. code-block:: shell

    $ curl -kX POST "https://localhost:5000/api/events" \
        --header "Content-Type: application/json" \
        --header "Authorization: Bearer $API_TOKEN" \
        -d @examples/cornerpy-2.json
    {
        "event_id": "<some-event-id>",
        "message": "event accepted"
    }

If you pay attention to your web/celery terminal you will see similar messages
to the ones that appeared when you previously loaded the data via the CLI
command.

Controlling indexing
~~~~~~~~~~~~~~~~~~~~

For completeness let's also import the last file, ``examples/cornerpy-3.json``,
but this time we'll instruct the APIs to skip the indexing part:

.. code-block:: shell

    # CLI method
    $ pipenv run asclepias-broker events load examples/cornerpy-3.json --no-index

    # ...or...

    # REST API method
    $ curl -k -X POST "https://localhost:5000/api/events?noindex=1" \
        --header "Content-Type: application/json" \
        --header "Authorization: Bearer $API_TOKEN" \
        -d @examples/cornerpy-3.json
    {
      "event_id": "<some-event-id>",
      "message": "event accepted"
    }

You might want to do this in case you want to import a lot of files/events and
then reindex everything afterwards (since indexing takes times as well). To
reindex everything you can run:

.. code-block:: shell

    # We pass the "--destroy" flag to clean the index state
    $ pipenv run asclepias-broker search reindex --destroy

Querying
--------

Now that we have loaded data into the broker we can proceed with performing
REST API queries to discover what kind of relationships corner.py has with
other papers/software.

Basic relationships
~~~~~~~~~~~~~~~~~~~

The most usual question one might want to answer, is how many citations does
**corner.py** have. The authors of **corner.py** recommend using `the JOSS
paper <http://dx.doi.org/10.21105/joss.00024>`_ with DOI
``10.21105/joss.00024`` for citations, so lets construct a query to search for
all relationships of type ``isCitedBy`` were this DOI is involved. You can
think of the following query's results as the answer to somebody asking
something like ``10.21105/joss.00024 isCitedBy _________``:

.. code-block:: shell

    # We can see that the paper has been cited 80 times...
    $ curl -k -G "https://localhost:5000/api/relationships" \
        --header "Accept: application/json" \
        -d id=10.21105/joss.00024 \
        -d scheme=doi \
        -d relation=isCitedBy \
        -d prettyprint=1
    {
      "hits": {
        "hits": [ ...<Scholix-formatted links>... ],
        "total": 80
      }
    }

This is fine, but there is an issue here: the fact that the authors of
**corner.py** wanted others to cite the software in a certain way,
unfortunately doesn't mean that everybody did so. We can quickly verify this by
querying for citations of specific versions of **corner.py**. Let's try
citations for **corner.py v1.0.2** (DOI ``10.5281/zenodo.45906``):

.. code-block:: shell

    # The DOI of v1.0.2 has been cited 14 times...
    $ curl -k -G "https://localhost:5000/api/relationships" \
        --header "Accept: application/json" \
        -d id=10.5281/zenodo.45906 \
        -d scheme=doi \
        -d relation=isCitedBy \
        -d prettyprint=1
    {
      ...
      "total": 14
      ...
    }

For those familiar though with the history of **corner.py**, the software used
to be named **triangle.py**. Let's see how many citations exist for
**triangle.py v0.1.1** (DOI ``10.5281/zenodo.11020``):

.. code-block:: shell

    # As we can see, there are 46 citations to "triangle.py v0.1.1"...
    $ curl -k -G "https://localhost:5000/api/relationships" \
        --header "Accept: application/json" \
        -d id=10.5281/zenodo.11020 \
        -d scheme=doi \
        -d relation=isCitedBy \
        -d prettyprint=1
    {
      ...
      "total": 46
      ...
    }

Grouped relationships
~~~~~~~~~~~~~~~~~~~~~

At this point, we can see that there is a clear issue when it comes to counting
citations for software that has been through multiple versions, name changes
and published papers. Perceptually though, all of these objects are just
different versions of the same thing, the software **corner.py**.

The broker allows performing a query that can answer the follwing interesting
question: *How many times has any version of corner.py been cited?*:

.. code-block:: shell

    # Note the "group_by=version" parameter...
    $ curl -k -G "https://localhost:5000/api/relationships" \
        --header "Accept: application/json" \
        -d id=10.21105/joss.00024 \
        -d scheme=doi \
        -d group_by=version \
        -d relation=isCitedBy \
        -d prettyprint=1
    {
      ...
      "total": 144
      ...
    }

Filtering
~~~~~~~~~

The broker's REST API also provides some basic filtering. E.g. one can find
all of the citations that were performed in the year 2016:

.. code-block:: shell

    # Note the "from" and "to" parameters...
    $ curl -k -G "https://localhost:5000/api/relationships" \
        --header "Accept: application/json" \
        -d id=10.21105/joss.00024 \
        -d scheme=doi \
        -d group_by=version \
        -d relation=isCitedBy \
        -d from="2016-01-01" -d to="2016-12-31" \
        -d prettyprint=1
    {
      ...
      "total": 50
      ...
    }
