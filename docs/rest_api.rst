..
    Copyright (C) 2018 CERN.

    Asclepias Broker is free software; you can redistribute it and/or modify it
    under the terms of the MIT License; see LICENSE file for more details.

REST API
========

The broker service currently exposes two REST API endpoints, one for the
ingestion of the

Events
------

.. http:post:: /events

    Submit an array of Scholix relationships to be ingested by the broker. This
    endpoint requires API token authentication in order to identify the
    user/source that submitted the events and to protect the service from spam.

    **Example request**:

    Submit Scholix relationships describing:

    - ``(2017ascl.soft02002F) IsIdenticalTo (10.21105/joss.00024)``
    - ``(2017JOSS.2017..188X) References (10.21105/joss.00024)``

    .. sourcecode:: http

        POST /events HTTP/1.1
        Authorization: Bearer <...API Token...>
        Content-Type: application/x-scholix-v3+json

        [
          {
            "Source": {
              "Identifier": {"ID": "2017ascl.soft02002F", "IDScheme": "ads"},
              "Type": {"Name": "software"}
            },
            "RelationshipType": {
              "Name": "IsRelatedTo",
              "SubType": "IsIdenticalTo",
              "SubTypeSchema": "DataCite"
            },
            "Target": {
              "Identifier": {"ID": "10.21105/joss.00024", "IDScheme": "doi"},
              "Type": {"Name": "software"}
            },
            "LinkProvider": [{"Name": "Zenodo"}],
            "LinkPublicationDate": "2018-01-01"
          },
          {
            "Source": {
              "Identifier": {"ID": "2017JOSS.2017..188X", "IDScheme": "ads"},
              "Type": {"Name": "unknown"}
            },
            "RelationshipType": {"Name": "References"},
            "Target": {
              "Identifier": {"ID": "10.21105/joss.00024", "IDScheme": "doi"},
              "Type": {"Name": "software"}
            },
            "LinkProvider": [{"Name": "SAO/NASA Astrophysics Data System"}],
            "LinkPublicationDate": "2017-04-01"
          }
        ]

    **Example response**:

    .. sourcecode:: http

        HTTP/1.1 202 OK
        Content-Type: application/json

        {
          "message": "event accepted",
          "event_id": "69270574-7cf4-477b-9b20-84554bb7032b"
        }

    :reqheader Authorization: API token to authenticate.
    :status 202: Event received successfully

Relationships
-------------

.. http:post:: /relationships

    Search for relationships of a specific identifier.

    **Example request**:

    Find ``isCitedBy`` relationships towards ``10.5281/zenodo.53155``:

    .. sourcecode:: http

        GET /relationships?id=10.5281/zenodo.53155&scheme=doi&relation=isCitedBy HTTP/1.1

    **Example response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/x-scholix-v3+json

        {
          "Source": {
            "Title": "corner.py v2.0.0",
            "Identifiers": [
              {"ID": "10.5281/zenodo.53155", "IDScheme": "doi"},
              {"ID": "https://zenodo.org/record/53155", "IDScheme": "url"},
              {"ID": "https://github.com/dfm/corner.py/tree/v2.0.0", "IDScheme": "url"}
            ],
            "Creator": [{"Name": "Dan Foreman-Mackey"}, {"Name": "Will Vousden"}],
            "Type": {"Name": "software"},
            "PublicationDate": "2016-05-26"
          },
          "Relation": {"Name": "isCitedBy"},
          "GroupBy": "identity",
          "Relationships": [
            {
              "Target": {
                "Title": "The mass distribution and gravitational...",
                "Type": {"Name": "literature"},
                "Identifiers": [
                  {"ID": "10.1093/mnras/stw2759", "IDScheme": "doi"},
                  {"ID": "https://doi.org/10.1093/mnras/stw2759", "IDScheme": "url"},
                ],
                "Creator": [{"Name": "Paul J. McMillan"}],
                "PublicationDate": "2016-10-26"
              },
              "LinkHistory": [
                {
                  "LinkPublicationDate": "2016-12-01",
                  "LinkProvider": {"Name": "Zenodo"}
                },
                {
                  "LinkPublicationDate": "2016-10-28",
                  "LinkProvider": {"Name": "ADS"}
                }
              ]
            },
            {
              "Target": {
                "Title": "PROBABILISTIC FORECASTING OF THE MASSES...",
                "Identifiers": [
                  {"ID": "10.3847/1538-4357/834/1/17", "IDScheme": "doi"},
                  {"ID": "https://doi.org/10.3847/1538-4357/834/1/17", "IDScheme": "url"}
                ],
                "Creator": [{"Name": "Jingjing Chen"}, {"Name": "David Kipping"}],
                "PublicationDate": "2016-12-27"
              },
              "LinkHistory": [
                {
                  "LinkPublicationDate": "2016-12-30",
                  "LinkProvider": {"Name": "ADS"}
                }
              ]
            }
          ]
        }

    :query id: Value of source identifer **(required)**.
      Example: ``10.5281/zenodo.1120265``
    :query scheme: Identifier scheme of the source identifier.
      Example: ``doi``, ``arxiv``, ``url``
    :query relation: Filter by type of the relation between source and
      target identifiers. Accepted values: ``cites``, ``isCitedBy``,
      ``isSupplementTo``, ``isSupplementedBy``, ``isRelatedTo``
    :query type: Filter by type of the target objects. Accepted values:
      ``literature``, ``software``, ``dataset``, ``unknown``
    :publication_year: Filter by the publication year of the target objects.
      Examples: ``2015--<2018`` (from incl. 2015 until excl. 2018), ``>2005--``
      (from excl. 2005), ``2015--2015`` (all from 2005).
    :query from: Filter by start date of publication/discovery of the
      relationships. Example: ``2018-01-02T13:30:00``
    :query to: Filter by end date of publication/discovery of the
      relationships. Example: ``2018-01-31``
    :query group_by: Expand the scope of the relationships to source
      identifier (default: ``identity``). Accepted values: ``identity``,
      ``version``
