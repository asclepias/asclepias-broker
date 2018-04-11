Asclepias prototype broker
==========================

This is a very early version of code for the Asclepias software broker. At the
moment this is not a web-enabled package - instead this is meant  to be used
programmatically from scripts with mock event streams to check the behavior.

To install::

    python setup.py install

This package requires Python 3.6 or later.

To test it out once installed, go inside the workflows directory and try and run
the ``run_example.py`` script, specifying the event stream to use as a command-line
argument. Each event stream is stored as a single JSON file. The state of the
broker is not preserved during successive runs of ``run_example.py``. Here is
a demonstration of this script::

    $ python run_example.py zenodo_simple_1.json

    ORGANIZATIONS
    -------------
    Organization: id=1 name=Zenodo identifier=None

    IDENTIFIERS
    -----------
    Identifier: id=10.5072/zenodo.11 id_schema=DOI id_url=https://doi.org
    Identifier: id=10.5072/zenodo.10 id_schema=DOI id_url=https://doi.org
    Identifier: id=https://zenodo.org/record/11 id_schema=URL id_url=None
    Identifier: id=10.5072/zenodo.53155 id_schema=DOI id_url=https://doi.org
    Identifier: id=10.5072/zenodo.56799 id_schema=DOI id_url=https://doi.org

    TYPES
    -----
    Type: id=1 name=literature sub_type=publication-article sub_type_schema=https://zenodo.org/schemas/records/record-v1.0.0.json#/resource_type/subtype

    OBJECTS
    -------
    Object: id=1 identifier_id=10.5072/zenodo.11 type_id=1 publisher_id=1 publication_date=2017-10-12
    Object: id=2 identifier_id=10.5072/zenodo.10 type_id=1 publisher_id=1 publication_date=2017-10-12

    RELATIONSHIPTYPES
    -----------------
    RelationshipType: id=1 scholix_relationship=IsRelatedTo original_relationship_name=IsIdenticalTo original_relationship_schema=DataCite
    RelationshipType: id=2 scholix_relationship=IsRelatedTo original_relationship_name=IsPartOf original_relationship_schema=DataCite
    RelationshipType: id=3 scholix_relationship=References original_relationship_name=Cites original_relationship_schema=DataCite

    RELATIONSHIPS
    -------------
    Relationship: id=1 source=10.5072/zenodo.11 relationship_type=1 target=https://zenodo.org/record/11
    Relationship: id=2 source=10.5072/zenodo.11 relationship_type=2 target=10.5072/zenodo.10
    Relationship: id=3 source=10.5072/zenodo.11 relationship_type=3 target=10.5072/zenodo.53155
    Relationship: id=4 source=10.5072/zenodo.11 relationship_type=3 target=10.5072/zenodo.56799

The code in this repository was funded by a grant from the Alfred P. Sloan
Foundation to the American Astronomical Society (2016).
