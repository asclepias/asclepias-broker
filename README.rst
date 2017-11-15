Asclepias prototype broker
==========================

This is a very early version of code for the Asclepias software broker. At the
moment this is not a web-enabled package - instead this is meant  to be used
programmatically from scripts with mock event streams to check the behavior.

To install::

    python setup.py install

To test it out once installed, go inside the workflows directory and try and run
the ``run_example.py`` script, specifying the event stream to use as a command-line
argument. Each event stream is stored as a single JSON file. The state of the
broker is not preserved during successive runs of ``run_example.py``. Here is
a demonstration of this script:

```
$ python run_example.py zenodo_simple_1.json
ORGANIZATIONs
-------------
Organization: id=1 name=Zenodo identifier=None

IDENTIFIERs
-----------
Identifier: id=10.5072/zenodo.11 id_schema=DOI id_url=https://doi.org
Identifier: id=10.5072/zenodo.10 id_schema=DOI id_url=https://doi.org

TYPEs
-----
Type: id=1 name=literature sub_type=publication-article sub_type_schema=https://zenodo.org/schemas/records/record-v1.0.0.json#/resource_type/subtype

OBJECTs
-------
Object: identifier_id=10.5072/zenodo.11 type_id=1 publisher_id=1 publication_date=2017-10-12
Object: identifier_id=10.5072/zenodo.10 type_id=1 publisher_id=1 publication_date=2017-10-12
```
