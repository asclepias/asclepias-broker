..
    Copyright (C) 2018 CERN.

    Asclepias Broker is free software; you can redistribute it and/or modify it
    under the terms of the MIT License; see LICENSE file for more details.

Data Model
==========

Events
------

:class:`Events <asclepias_broker.events.models.Event>` are a *vessel* for data
to arrive to the broker. The event data is ingested in order to be broken down
to :class:`Object Events <asclepias_broker.events.models.ObjectEvent>` and
eventually into :class:`Identifiers <asclepias_broker.core.models.Identifier>`,
:class:`Relationships <asclepias_broker.core.models.Relationship>` and
:ref:`metadata`. These entities are then processed and integrated into the
existing data to enhance the knowledge that the broker service possesses.

.. image:: ../images/data-model-events.svg
   :alt: Events data model

Graph
-----

:class:`Identifiers <asclepias_broker.core.models.Identifier>` represent
references to scholarly entities and follow a specific identifier scheme (e.g.
``DOI``, ``arXiv``, ``URL``, etc). :class:`Relationships
<asclepias_broker.core.models.Relationship>` have a type (e.g.
``isIdenticalTo``, ``hasVersion``, ``cites``, etc.) and exist between two
identifiers, the source and the target. These are the building blocks for the
broker's graph model

To represent scholarly entities (software, articles, etc.), the concept of
:class:`Groups <asclepias_broker.graph.models.Group>` is introduced. Groups
define a set of **Identifiers** which are formed based on the **Relationships**
between them. For example, one can define that all **Identifiers** that have
Relationships of type ``isIdenticalTo`` form a Group of type ``Identity`` and
can be considered as a single entity.

.. image:: ../images/data-model-graph-1.svg
   :alt: Identifer group

One can also define Groups of Groups. For example ``Identity`` Groups with
Identifiers that have a ``hasVersion`` relationship with Identifiers from other
``Identity`` Groups, can form a ``Version`` Group.

.. image:: ../images/data-model-graph-2.svg
   :alt: Version group

One can then finally model relationships between scholarly entities (e.g.
*Paper A cites Software X*), by abstracting the low-level Relationships between
Identifiers to the Group level and thus form :class:`Group Relationships
<asclepias_broker.graph.models.GroupRelationship>`. For example, one can define
that ``Identity`` Groups of Identifiers that have Relationships of type
``cites`` to Identifiers of other ``Identity`` Groups, can form a ``cites``
Group Relationship.

.. image:: ../images/data-model-graph-3.svg
   :alt: Group relationship

.. _metadata:

Metadata
--------

Identifiers, Relationships and Groups can form complex graphs. While this is
important for discovering connections between them, it is also valuable to be
able to retrieve information about the objects they hold references to. In
order to facilitate this information, :class:`Group Metadata
<asclepias_broker.metadata.models.GroupMetadata>` and :class:`Group
Relationship Metadata
<asclepias_broker.metadata.models.GroupRelationshipMetadata>` is stored for
**Groups** and **Group Relationships** respectively.

This metadata can be used for e.g. rendering a proper citation when needed,
filtering.

.. image:: ../images/data-model-metadata.svg
   :alt: Metadata data model

Persistence
-----------

As described in the previous sections, the broker receives raw events that are
then processed to produce a graph. The data goes through a transformation
pipeline that at various stages requires persisting its inputs and outputs.
This persistence takes place in an RDBMS, like PostgreSQL or SQLite.

We can divide the persisted information into three incremental levels:

.. figure:: ../images/data-model-layers.svg
   :alt: Information layers
   :align: right

**A) Raw data**
  The raw event payloads that arrive into the system

**B) Ground truth**
  Normalized form of the raw data, representing deduplicated facts about
  Identifiers and Relationships

**C) Processed knowledge**
  Information that is extracted from the ground truth and is transformed into
  structured knowledge

Each level depends on all of its predecessors. This means that if there is an
issue on e.g. level C, levels A and B are enough to rebuild it. In the same
fashion, level B depends only on level A.

.. note::

   All of the above models map to actual database schema tables. For the sake
   of clarity though, intermediary tables that represent many-to-many
   relationships between these models (e.g.
   :class:`~asclepias_broker.graph.models.GroupM2M` for ``Group <-> Group``
   relationships) were not included.

Search
------

.. figure:: ../images/data-model-search.svg
   :align: right

Now that we have the above information stored persistently in the system, we
need an efficient way to perform queries over it. Doing this directly through
the database would seem like a practical, although naive, solution for fetching
this information. Our graph representation spreads over many tables, which
means that fetching it would require multiple complex joins. On top of that our
metadata is stored in JSON/blob-like columns, where filtering is slow and
inefficient.


The way to tackle this issue, is to denormalize our data back into a rich
document representation that clients of the service can consume with ease. This
can be easily done via the use of a document-based store (aka *NoSQL*) system,
like Elasticsearch.

We can create and index the documents using the following strategy:

1. For each **Group Relationship** in our system:
    a. Fetch its **Group Relationships Metadata**
    b. For its source and target groups:
        i. Fetch the **Group Metadata** and **Identifiers**
    c. Create a document from the fetched information and index it

By performing the expensive database queries only once in order to index the
denormalized documents we have managed to get the best of both worlds: a
relationally consistent graph (backed by RDB constraints) which is easy to
perform complex queries over (backed by Elasticsearch).

Consistency
~~~~~~~~~~~

A downside to this solution is that the state of our document store is not
always in sync with what we have in our graph in the database. This issue
originates from the fact that changes in the database are automatically
protected via foreign-key and unique constraints that cannot be applied with
the same ease in a document-based store.

A solution to this is to periodically rebuild the entire index from scratch.
This guarantees that Elasticsearch starts from a blank state, with no "orphan"
or stale information lying around. Also, using some of Elasticsearch's features
this index rebuilding process can be achieved without affecting the
responsiveness of the service.
