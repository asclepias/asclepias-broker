"""Test broker metadata model."""
import pytest
from jsonschema.exceptions import ValidationError

from asclepias_broker.models import Group, GroupMetadata, \
    GroupRelationship, GroupRelationshipMetadata, GroupType, Relation


def update_and_compare(sess, m, payload, expected=None):
    try:
        m.update(payload)
        sess.commit()
        sess.refresh(m)
        assert m.json == (expected or payload)
    except Exception:
        raise
    finally:
        sess.refresh(m)


def test_group_metadata(broker):
    sess = broker.session
    g = Group(type=GroupType.Identity)
    sess.add(g)
    sess.commit()
    gm = GroupMetadata(group_id=g.id)
    sess.add(gm)
    sess.commit()
    assert g.data == gm
    assert g.data.json == gm.json

    # Minimal metadata
    update_and_compare(sess, gm, {'Title': 'Some title'})
    # Change title
    update_and_compare(sess, gm, {'Title': 'Some other title'})
    # Null payload
    update_and_compare(sess, gm, {}, {'Title': 'Some other title'})
    # Null title
    update_and_compare(
        sess, gm, {'Title': None}, {'Title': 'Some other title'})
    # Add creators
    update_and_compare(
        sess, gm,
        {'Creator': [{'Name': 'Foo creator'}]},
        {'Title': 'Some other title', 'Creator': [{'Name': 'Foo creator'}]},
    )
    # Change creators
    update_and_compare(
        sess, gm,
        {'Creator': [{'Name': 'Bar creator'}]},
        {'Title': 'Some other title', 'Creator': [{'Name': 'Bar creator'}]},
    )
    # Invalid payload data
    with pytest.raises(ValidationError):
        update_and_compare(sess, gm, {'Title': 1234})
    # Full metadata
    update_and_compare(
        sess, gm,
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


def test_group_relationship_metadata(broker):
    sess = broker.session
    g_src = Group(type=GroupType.Identity)
    g_trg = Group(type=GroupType.Identity)
    sess.add_all((g_src, g_trg))
    sess.commit()
    gr = GroupRelationship(
        type=GroupType.Identity, relation=Relation.Cites,
        source_id=g_src.id, target_id=g_trg.id)
    sess.add(gr)
    sess.commit()
    grm = GroupRelationshipMetadata(group_relationship_id=gr.id)
    sess.add(grm)
    sess.commit()
    assert gr.data == grm
    assert gr.data.json == grm.json

    # Minimal metadata
    update_and_compare(
        sess, grm,
        {'LinkPublicationDate': '2018-01-01',
         'LinkProvider': [{'Name': 'Foobar'}]},
        [{'LinkPublicationDate': '2018-01-01',
          'LinkProvider': [{'Name': 'Foobar'}]}]
    )
    # Add provider item
    update_and_compare(
        sess, grm,
        {'LinkPublicationDate': '2018-01-02',
         'LinkProvider': [{'Name': 'Bazqux'}]},
        [{'LinkPublicationDate': '2018-01-01',
          'LinkProvider': [{'Name': 'Foobar'}]},
         {'LinkPublicationDate': '2018-01-02',
          'LinkProvider': [{'Name': 'Bazqux'}]}]
    )
    # Invalid schema
    with pytest.raises(ValidationError):
        update_and_compare(sess, grm, {'invalid': 'field'})
    # Full relationship metadata
    update_and_compare(
        sess, grm,
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
