..
    Copyright (C) 2018 CERN.
    Copyright (c) 2017 Thomas P. Robitaille.

    Asclepias Broker is free software; you can redistribute it and/or modify it
    under the terms of the MIT License; see LICENSE file for more details.

==================
 Asclepias Broker
==================

.. image:: https://img.shields.io/travis/asclepias/asclepias-broker.svg
        :target: https://travis-ci.org/asclepias/asclepias-broker

.. image:: https://img.shields.io/coveralls/asclepias/asclepias-broker.svg
        :target: https://coveralls.io/r/asclepias/asclepias-broker

.. image:: https://img.shields.io/github/license/asclepias/asclepias-broker.svg
        :target: https://github.com/asclepias/asclepias-broker/blob/master/LICENSE

The Asclepias Broker is a web service that facilitates building and flexibly
searching graphs of links between research outputs.

Further documentation is available on https://asclepias-broker.readthedocs.io/

The Asclepias Broker is a service aiming to address a couple of problems in the
world of scholarly link communication, with a focus on Software citation:

**Governance of the scholarly links data and metadata**
  Storage and curation of scholarly links is a problem that cannot be easily
  solved in a centralized fashion. In the same manner that specialized
  repositories exist to facilitate research output of different scientific
  fields, scholarly link tracking is a task performed best by a service that
  specializes in a specific scientific field.

**Meaningful counting of software citations**
  Software projects (and other types of research) evolve over time, and these
  changes are tracked via the concept of versioning. The issue that rises is
  that citations to software projects end up being "diluted" throughout their
  versions, leading to inaccurate citation counting for the entire sotware
  project. Rolling-up these citations is critical to assess the impact a
  software project has in a scientific field.

**Sharing of scholarly links across interested parties**
  Keeping track of the incoming scholarly links for a research artifact is a
  difficult task that usually repositories have to individually tackle by
  tapping into a multitude of external services, that expose their data in
  different ways. Receiving "live" notifications and having a consistent format
  and source for these events is crucial in order to reduce complexity and
  provide a comprehensive view.

These problems are addressed by providing an easy to setup service that:

* Can receive and store scholarly links through a REST API
* Exposes these scholarly links through a versatile REST API
* Can connect to a network of similar services and exchange links with them

The code in this repository was funded by a grant from the Alfred P. Sloan
Foundation to the American Astronomical Society (2016).
