# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 CERN.
#
# Asclepias Broker is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Test broker metadata model."""
import pytest
from invenio_db import db
from jsonschema.exceptions import ValidationError

from asclepias_broker.core.models import Relation
from asclepias_broker.graph.models import Group, GroupRelationship, GroupType
from asclepias_broker.metadata.models import GroupMetadata, \
    GroupRelationshipMetadata


def update_and_compare(m, payload, expected=None):
    try:
        m.update(payload)
        db.session.commit()
        db.session.refresh(m)
        assert m.json == (expected or payload)
    except Exception:
        raise
    finally:
        db.session.refresh(m)


def test_group_metadata(db):
    g = Group(type=GroupType.Identity)
    db.session.add(g)
    db.session.commit()
    gm = GroupMetadata(group_id=g.id)
    db.session.add(gm)
    db.session.commit()
    assert g.data == gm
    assert g.data.json == gm.json

    # Minimal metadata
    update_and_compare(
        gm,
        {'Title': 'Some title'},
        {'Title': 'Some title', 'Type': {'Name': 'unknown'}})
    # Change title
    update_and_compare(
        gm,
        {'Title': 'Some other title'},
        {'Title': 'Some other title', 'Type': {'Name': 'unknown'}})
    # Null payload
    update_and_compare(
        gm,
        {},
        {'Title': 'Some other title', 'Type': {'Name': 'unknown'}})
    # Null title
    update_and_compare(
        gm,
        {'Title': None},
        {'Title': 'Some other title', 'Type': {'Name': 'unknown'}})
    # Add creators
    update_and_compare(
        gm,
        {'Creator': [{'Name': 'Foo creator'}]},
        {'Title': 'Some other title', 'Type': {'Name': 'unknown'},
         'Creator': [{'Name': 'Foo creator'}]},
    )
    # Change creators
    update_and_compare(
        gm,
        {'Creator': [{'Name': 'Bar creator'}]},
        {'Title': 'Some other title', 'Type': {'Name': 'unknown'},
         'Creator': [{'Name': 'Bar creator'}]},
    )
    # Invalid payload data
    with pytest.raises(ValidationError):
        update_and_compare(gm, {'Title': 1234})
    # Full metadata
    update_and_compare(
        gm,
        {'Type': {'Name': 'literature',
                  'SubType': 'journal article',
                  'SubTypeSchema': 'datacite'},
         'PublicationDate': '2018-01-01',
         'Creator': [{'Name': 'Foo creator',
                      'Identifier': [{'ID': '0000-0001-2345-6789',
                                      'IDScheme': 'orcid'}]}]},
        {'Title': 'Some other title',
         'Type': {'Name': 'literature',
                  'SubType': 'journal article',
                  'SubTypeSchema': 'datacite'},
         'PublicationDate': '2018-01-01',
         'Creator': [{'Name': 'Foo creator',
                      'Identifier': [{'ID': '0000-0001-2345-6789',
                                      'IDScheme': 'orcid'}]}]},
    )


def test_group_metadata_update_type(db):
    g = Group(type=GroupType.Identity)
    db.session.add(g)
    db.session.commit()
    minimal_gm = {'Type': {'Name': 'unknown'}}
    gm = GroupMetadata(group_id=g.id, json=minimal_gm)
    db.session.add(gm)
    db.session.commit()
    assert g.data == gm
    assert g.data.json == gm.json

    # Add Type
    update_and_compare(gm, {'Title': 'Some other title',
                            'Type': {'Name': 'unknown'}})

    # Change Type
    update_and_compare(gm, {'Title': 'Some other title',
                            'Type': {'Name': 'software'}})

    # Don't override Type
    update_and_compare(gm, {'Type': {}}, {'Title': 'Some other title',
                                          'Type': {'Name': 'software'}})
    update_and_compare(gm, {'Type': {'Name': 'unknown'}},
                       {'Title': 'Some other title',
                        'Type': {'Name': 'software'}})

    # Change Type
    update_and_compare(gm, {'Type': {'Name': 'dataset'}},
                       {'Title': 'Some other title',
                        'Type': {'Name': 'dataset'}})


def test_group_relationship_metadata(db):
    g_src = Group(type=GroupType.Identity)
    g_trg = Group(type=GroupType.Identity)
    db.session.add_all((g_src, g_trg))
    db.session.commit()
    gr = GroupRelationship(
        type=GroupType.Identity, relation=Relation.Cites,
        source_id=g_src.id, target_id=g_trg.id)
    db.session.add(gr)
    db.session.commit()
    grm = GroupRelationshipMetadata(group_relationship_id=gr.id)
    db.session.add(grm)
    db.session.commit()
    assert gr.data == grm
    assert gr.data.json == grm.json

    # Minimal metadata
    update_and_compare(
        grm,
        {'LinkPublicationDate': '2018-01-01',
         'LinkProvider': [{'Name': 'Foobar'}]},
        [{'LinkPublicationDate': '2018-01-01',
          'LinkProvider': [{'Name': 'Foobar'}]}]
    )
    # Add provider item
    update_and_compare(
        grm,
        {'LinkPublicationDate': '2018-01-02',
         'LinkProvider': [{'Name': 'Bazqux'}]},
        [{'LinkPublicationDate': '2018-01-01',
          'LinkProvider': [{'Name': 'Foobar'}]},
         {'LinkPublicationDate': '2018-01-02',
          'LinkProvider': [{'Name': 'Bazqux'}]}]
    )
    # Invalid schema
    with pytest.raises(ValidationError):
        update_and_compare(grm, {'invalid': 'field'})
    # Full relationship metadata
    update_and_compare(
        grm,
        {'LinkPublicationDate': '2018-01-02',
         'LinkProvider': [{'Name': 'Test provider',
                           'Identifier': [{'ID': 'https://provider.com',
                                           'IDScheme': 'url'}]}],
         'LicenseURL': 'https://creativecommons.org/publicdomain/zero/1.0/'},
        [{'LinkPublicationDate': '2018-01-01',
          'LinkProvider': [{'Name': 'Foobar'}]},
         {'LinkPublicationDate': '2018-01-02',
          'LinkProvider': [{'Name': 'Bazqux'}]},
         {'LinkPublicationDate': '2018-01-02',
          'LinkProvider': [{'Name': 'Test provider',
                            'Identifier': [{'ID': 'https://provider.com',
                                            'IDScheme': 'url'}]}],
          'LicenseURL': 'https://creativecommons.org/publicdomain/zero/1.0/'}]
    )
