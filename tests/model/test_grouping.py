# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 CERN.
#
# Asclepias Broker is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Test broker model."""
import pytest

from invenio_db import db

from asclepias_broker.models import Relationship, Relation, Identifier,\
    Group, GroupType, Identifier2Group, GroupM2M, GroupRelationship,\
    GroupRelationshipM2M, Relationship2GroupRelationship, GroupMetadata,\
    GroupRelationshipMetadata

from asclepias_broker.tasks import get_or_create_groups, merge_version_groups, \
    merge_identity_groups, get_group_from_id

from helpers import generate_payloads, assert_grouping, \
    create_objects_from_relations


def _handle_events(broker, evtsrc):
    events = generate_payloads(evtsrc)
    for ev in events:
        broker.handle_event(ev)


def off_test_simple_id_group_merge(broker):
    """Test simple ID groups merging."""
    evtsrc = [
        ['C', 'A', 'IsIdenticalTo', 'B', '2018-01-01'],
    ]
    _handle_events(broker, evtsrc)
    # {'A', 'B'}
    assert Group.query.count() == 2
    vg = Group.query.filter_by(type=GroupType.Version).one()
    vi = Group.query.filter_by(type=GroupType.Identity).one()
    assert Identifier.query.count() == 2
    assert Relationship.query.count() == 1
    assert Identifier2Group.query.count() == 2
    evtsrc = [
        ['C', 'A', 'IsIdenticalTo', 'C', '2018-01-01'],
    ]
    _handle_events(broker, evtsrc)
    # {'A', 'B', 'C'}
    assert Group.query.count() == 1
    assert Identifier.query.count() == 3
    assert Identifier2Group.query.count() == 3

    evtsrc = [
        ['C', 'D', 'IsIdenticalTo', 'E', '2018-01-01'],
    ]
    _handle_events(broker, evtsrc)
    # {'A', 'B', 'C'}, {'D', 'E'}
    assert Group.query.count() == 2
    assert Identifier.query.count() == 5
    assert Identifier2Group.query.count() == 5

    evtsrc = [
        ['C', 'A', 'IsIdenticalTo', 'D', '2018-01-01'],
    ]
    _handle_events(broker, evtsrc)
    # {'A', 'B', 'C', 'D', 'E'}
    assert Group.query.count() == 1
    assert Identifier.query.count() == 5
    assert Identifier2Group.query.count() == 5


def test_get_or_create_groups(broker):
    """Test creating groups (Identity and Version) for an identifier."""
    id1 = Identifier(value='A', scheme='doi')
    db.session.add(id1)
    #id2 = Identifier(value='B', scheme='doi')
    #rel = Relationship(source=id1, target=id2, relation=Relation.IsIdenticalTo)
    assert not Group.query.count()
    assert not GroupM2M.query.count()
    assert not Identifier2Group.query.count()
    id_g, ver_g = get_or_create_groups(id1)
    db.session.commit()

    def _check_groups(identifier, id_g, ver_g):
        assert Group.query.count() == 2
        assert GroupM2M.query.count() == 1
        assert Identifier2Group.query.count() == 1
        assert Group.query.filter_by(type=GroupType.Identity).one() == id_g
        assert Group.query.filter_by(type=GroupType.Version).one() == ver_g
        id2g = Identifier2Group.query.one()
        g2g = GroupM2M.query.one()
        assert id2g.identifier == identifier
        assert id2g.group == id_g
        assert g2g.group == ver_g
        assert g2g.subgroup == id_g

    _check_groups(id1, id_g, ver_g)

    # Fetch the ID again and try to create groups again
    id2 = Identifier.get('A', 'doi')
    assert id2
    id_g, ver_g = get_or_create_groups(id1)
    db.session.commit()

    # Make sure nothing changed
    _check_groups(id2, id_g, ver_g)

    # Add a new, separate identifier
    id3 = Identifier(value='B', scheme='doi')
    db.session.add(id3)
    id_g, ver_g = get_or_create_groups(id3)

    assert Group.query.count() == 4
    assert GroupM2M.query.count() == 2
    assert Identifier2Group.query.count() == 2


def test_merge_version_groups(broker):
    """Test group merging.

    Note: This test is merging Version groups. This does not automatically
          merge the Identity groups below!
    """
    rels = [
        ('C', Relation.Cites, 'A'),
        ('C', Relation.Cites, 'B'),
        ('A', Relation.Cites, 'D'),
        ('B', Relation.Cites, 'D'),
        ('E', Relation.Cites, 'B'),
        ('E', Relation.IsRelatedTo, 'B'),
        ('A', Relation.Cites, 'F'),
        ('A', Relation.IsRelatedTo, 'F'),
    ]
    create_objects_from_relations(rels)

    grouping = (
        [
            ['A'],
            ['B'],
            ['C'],
            ['D'],
            ['E'],
            ['F'],  # Idx=5
            [0],
            [1],
            [2],
            [3],
            [4],
            [5],
        ],
        [
            ('C', Relation.Cites, 'A'),
            ('C', Relation.Cites, 'B'),
            ('A', Relation.Cites, 'D'),
            ('B', Relation.Cites, 'D'),
            ('E', Relation.Cites, 'B'),
            ('E', Relation.IsRelatedTo, 'B'),
            ('A', Relation.Cites, 'F'),
            ('A', Relation.IsRelatedTo, 'F'),
            # Identity group relations:
            (2, Relation.Cites, 0),
            (2, Relation.Cites, 1),
            (0, Relation.Cites, 3),
            (1, Relation.Cites, 3),
            (4, Relation.Cites, 1),
            (4, Relation.IsRelatedTo, 1),
            (0, Relation.Cites, 5),
            (0, Relation.IsRelatedTo, 5),
            # Version group relations:
            (8, Relation.Cites, 6),
            (8, Relation.Cites, 7),
            (6, Relation.Cites, 9),
            (7, Relation.Cites, 9),
            (10, Relation.Cites, 7),
            (10, Relation.IsRelatedTo, 7),
            (6, Relation.Cites, 11),
            (6, Relation.IsRelatedTo, 11),
        ],
        [
            (8, [0]),
            (9, [1]),
            (10, [2]),
            (11, [3]),
            (12, [4]),
            (13, [5]),
            (14, [6]),
            (15, [7]),
            (16, [8]),
            (17, [9]),
            (18, [10]),
            (19, [11]),
            (20, [12]),
            (21, [13]),
            (22, [14]),
            (23, [15]),
        ]
    )

    assert_grouping(grouping)

    # Merge Version groups of A and B
    # This merges only the version groups, not Identity groups

    id_grp1 = get_group_from_id('A', group_type=GroupType.Version)
    id_grp2 = get_group_from_id('B', group_type=GroupType.Version)
    merge_version_groups(id_grp1, id_grp2)
    db.session.commit()

    # Version groups and relations after merging:
    # C-Cites-AB (squashed C-Cites-A and C-Cites-B)
    # AB-Cites-D (squashed A-Cites-D and B-Cites-D)
    # E-Cites-AB
    # E-IsRelatedTo-AB (not squashed with above, because of different relation)
    # AB-Cites-F
    # AB-IsRelatedTo-F (not squashed with above, because of different relation)

    grouping = (
        [
            ['A'],
            ['B'],
            ['C'],
            ['D'],
            ['E'],
            ['F'],  # Idx=5
            [0, 1],  # {AB}
            [2],  # {C}
            [3],  # {D}
            [4],  # {E}
            [5],  # {F}
        ],
        [
            ('C', Relation.Cites, 'A'),
            ('C', Relation.Cites, 'B'),
            ('A', Relation.Cites, 'D'),
            ('B', Relation.Cites, 'D'),
            ('E', Relation.Cites, 'B'),
            ('E', Relation.IsRelatedTo, 'B'),
            ('A', Relation.Cites, 'F'),
            ('A', Relation.IsRelatedTo, 'F'),
            # Identity group relations:
            (2, Relation.Cites, 0),  # C-Cites-A  Idx=8
            (2, Relation.Cites, 1),  # C-Cites-B
            (0, Relation.Cites, 3),  # A-Cites-D
            (1, Relation.Cites, 3),  # B-Cites-D
            (4, Relation.Cites, 1),  # E-Cites-B
            (4, Relation.IsRelatedTo, 1),  # E-IsRelatedTo-B
            (0, Relation.Cites, 5),  # A-Cites-F
            (0, Relation.IsRelatedTo, 5),  # A-IsRelatedTo-F
            # Version group relations:
            (7, Relation.Cites, 6),  # C-Cites-AB  Idx=16
            (6, Relation.Cites, 8),  # AB-Cites-D
            (9, Relation.Cites, 6),  # E-Cites-AB
            (9, Relation.IsRelatedTo, 6),  # E-IsRelatedTo-AB
            (6, Relation.Cites, 10),  # AB-Cites-F
            (6, Relation.IsRelatedTo, 10),  # AB-IsRelatedTo-F
        ],
        [
            (8, [0]),
            (9, [1]),
            (10, [2]),
            (11, [3]),
            (12, [4]),
            (13, [5]),
            (14, [6]),
            (15, [7]),
            (16, [8, 9]),
            (17, [10, 11]),
            (18, [12]),
            (19, [13]),
            (20, [14]),
            (21, [15]),
        ]
    )

    assert_grouping(grouping)

    # Merge Version groups of C and D and also E and F

    id_grp1 = get_group_from_id('C', group_type=GroupType.Version)
    id_grp2 = get_group_from_id('D', group_type=GroupType.Version)
    merge_version_groups(id_grp1, id_grp2)

    id_grp1 = get_group_from_id('E', group_type=GroupType.Version)
    id_grp2 = get_group_from_id('F', group_type=GroupType.Version)
    merge_version_groups(id_grp1, id_grp2)
    db.session.commit()

    # Version groups and relations after merging:
    # CD-Cites-AB (squashed C-Cites-A and C-Cites-B)
    # AB-Cites-CD (squashed A-Cites-D and B-Cites-D)
    # EF-Cites-AB
    # EF-IsRelatedTo-AB
    # AB-Cites-EF
    # AB-IsRelatedTo-EF

    grouping = (
        [
            ['A'],
            ['B'],
            ['C'],
            ['D'],
            ['E'],
            ['F'],  # Idx=5
            [0, 1],  # {AB}
            [2, 3],  # {CD}
            [4, 5],  # {EF}
        ],
        [
            ('C', Relation.Cites, 'A'),
            ('C', Relation.Cites, 'B'),
            ('A', Relation.Cites, 'D'),
            ('B', Relation.Cites, 'D'),
            ('E', Relation.Cites, 'B'),
            ('E', Relation.IsRelatedTo, 'B'),
            ('A', Relation.Cites, 'F'),
            ('A', Relation.IsRelatedTo, 'F'),
            # Identity group relations:
            (2, Relation.Cites, 0),  # C-Cites-A  Idx=8
            (2, Relation.Cites, 1),  # C-Cites-B
            (0, Relation.Cites, 3),  # A-Cites-D
            (1, Relation.Cites, 3),  # B-Cites-D
            (4, Relation.Cites, 1),  # E-Cites-B
            (4, Relation.IsRelatedTo, 1),  # E-IsRelatedTo-B
            (0, Relation.Cites, 5),  # A-Cites-F
            (0, Relation.IsRelatedTo, 5),  # A-IsRelatedTo-F
            # Version group relations:
            (7, Relation.Cites, 6),  # CD-Cites-AB  Idx=16
            (6, Relation.Cites, 7),  # AB-Cites-CD
            (8, Relation.Cites, 6),  # EF-Cites-AB
            (8, Relation.IsRelatedTo, 6),  # EF-IsRelatedTo-AB
            (6, Relation.Cites, 8),  # AB-Cites-EF
            (6, Relation.IsRelatedTo, 8),  # AB-IsRelatedTo-EF
        ],
        [
            (8, [0]),
            (9, [1]),
            (10, [2]),
            (11, [3]),
            (12, [4]),
            (13, [5]),
            (14, [6]),
            (15, [7]),
            (16, [8, 9]),
            (17, [10, 11]),
            (18, [12]),
            (19, [13]),
            (20, [14]),
            (21, [15]),
        ]
    )
    assert_grouping(grouping)


def test_merge_identity_groups(broker):
    """Test group merging.

    Note: This test is merging Version groups until only one is left.
        This does not automatically merge the Identity groups below!
    """
    rels = [
        ('A', Relation.Cites, 'C'),
        ('B', Relation.Cites, 'C'),
        ('D', Relation.Cites, 'A'),
        ('D', Relation.Cites, 'B'),
    ]
    metadata = [
        (
            {'Title': 'Title of A v1',
             'Type': {'Name': 'literature',
                      'SubType': 'journal article',
                      'SubTypeSchema': 'datacite'},
             'PublicationDate': '2018-01-01',
             'Creator': [{'Name': 'Creator A v1',
                          'Identifier': [{'ID': '0000-0001-2345-6789',
                                          'IDScheme': 'orcid'}]}]},
            {'LinkPublicationDate': '2018-01-01',
              'LinkProvider': [{'Name': 'Foobar'}]},
            {'Title': 'Title of C v1',
             'Type': {'Name': 'literature',
                      'SubType': 'journal article',
                      'SubTypeSchema': 'datacite'},
             'PublicationDate': '2018-01-01',
             'Creator': [{'Name': 'Creator C v1',
                          'Identifier': [{'ID': '0000-0001-2345-6789',
                                          'IDScheme': 'orcid'}]}]}
        ),
        (
            {'Title': 'Title of B v1',
             'Type': {'Name': 'literature',
                      'SubType': 'journal article',
                      'SubTypeSchema': 'datacite'},
             'PublicationDate': '2018-01-01',
             'Creator': [{'Name': 'Creator B v1',
                          'Identifier': [{'ID': '0000-0001-2345-6789',
                                          'IDScheme': 'orcid'}]}]},
            {'LinkPublicationDate': '2018-01-01',
              'LinkProvider': [{'Name': 'Foobar'}]},
            {'Title': 'Title of C v2',
             'Type': {'Name': 'literature',
                      'SubType': 'journal article',
                      'SubTypeSchema': 'datacite'},
             'PublicationDate': '2018-01-01',
             'Creator': [{'Name': 'Creator C v2',
                          'Identifier': [{'ID': '0000-0001-2345-6789',
                                          'IDScheme': 'orcid'}]}]}
        ),
        (
            {'Title': 'Title of D v1',
             'Type': {'Name': 'literature',
                      'SubType': 'journal article',
                      'SubTypeSchema': 'datacite'},
             'PublicationDate': '2018-01-01',
             'Creator': [{'Name': 'Creator D v1',
                          'Identifier': [{'ID': '0000-0001-2345-6789',
                                          'IDScheme': 'orcid'}]}]},
            {'LinkPublicationDate': '2018-01-01',
              'LinkProvider': [{'Name': 'Foobar'}]},
            {'Title': 'Title of A v2',
             'Type': {'Name': 'literature',
                      'SubType': 'journal article',
                      'SubTypeSchema': 'datacite'},
             'PublicationDate': '2018-01-01',
             'Creator': [{'Name': 'Creator A v2',
                          'Identifier': [{'ID': '0000-0001-2345-6789',
                                          'IDScheme': 'orcid'}]}]}
        ),
        (
            {'Title': 'Title of D v2',
             'Type': {'Name': 'literature',
                      'SubType': 'journal article',
                      'SubTypeSchema': 'datacite'},
             'PublicationDate': '2018-01-01',
             'Creator': [{'Name': 'Creator D v2',
                          'Identifier': [{'ID': '0000-0001-2345-6789',
                                          'IDScheme': 'orcid'}]}]},
            {'LinkPublicationDate': '2018-01-01',
              'LinkProvider': [{'Name': 'Foobar'}]},
            {'Title': 'Title of B v2',
             'Type': {'Name': 'literature',
                      'SubType': 'journal article',
                      'SubTypeSchema': 'datacite'},
             'PublicationDate': '2018-01-01',
             'Creator': [{'Name': 'Creator B v2',
                          'Identifier': [{'ID': '0000-0001-2345-6789',
                                          'IDScheme': 'orcid'}]}]}
        )
    ]
    create_objects_from_relations(rels, metadata=metadata)

    grouping = (
        # Groups and GroupM2M
        [
            # Identity groups
            ['A'],
            ['B'],
            ['C'],
            ['D'],
            # Version groups
            [0],
            [1],
            [2],
            [3],
        ],
        # Relationships
        [
            # Identifier relationships
            ('A', Relation.Cites, 'C'),
            ('B', Relation.Cites, 'C'),
            ('D', Relation.Cites, 'A'),
            ('D', Relation.Cites, 'B'),
            # Identity group relationships:
            (0, Relation.Cites, 2),
            (1, Relation.Cites, 2),
            (3, Relation.Cites, 0),
            (3, Relation.Cites, 1),
            # Version group relationships:
            (4, Relation.Cites, 6),
            (5, Relation.Cites, 6),
            (7, Relation.Cites, 4),
            (7, Relation.Cites, 5),
        ],
        # Relationships M2M
        [
            (4, [0]),
            (5, [1]),
            (6, [2]),
            (7, [3]),
            (8, [4]),
            (9, [5]),
            (10, [6]),
            (11, [7]),
        ]
    )

    assert_grouping(grouping)

    # Merge Version groups of A and B
    # This merges only the version groups, not Identity groups
    id_grp1 = get_group_from_id('A')
    id_grp2 = get_group_from_id('B')
    merge_identity_groups(id_grp1, id_grp2)
    db.session.commit()

    # Version groups and relations after merging:
    # C-Cites-AB (squashed C-Cites-A and C-Cites-B)
    # AB-Cites-D (squashed A-Cites-D and B-Cites-D)
    # E-Cites-AB
    # E-IsRelatedTo-AB (not squashed with above, because of different relation)
    # AB-Cites-F
    # AB-IsRelatedTo-F (not squashed with above, because of different relation)

    grouping = (
        [
            ['A', 'B'],
            ['C'],
            ['D'],
            [0],  # {AB}
            [1],  # {C}
            [2],  # {D}
        ],
        [
            ('A', Relation.Cites, 'C'),
            ('B', Relation.Cites, 'C'),
            ('D', Relation.Cites, 'A'),
            ('D', Relation.Cites, 'B'),
            # Identity group relations:
            (0, Relation.Cites, 1),  # AB-Cites-C
            (2, Relation.Cites, 0),  # D-Cites-AB
            # Version group relations:
            (3, Relation.Cites, 4),  # AB-Cites-C
            (5, Relation.Cites, 3),  # D-CItes-AB
        ],
        [
            (4, [0, 1, ]),
            (5, [2, 3, ]),
            (6, [4]),
            (7, [5]),
        ]
    )

    assert_grouping(grouping)
    # Merge Version groups of C and D
    id_grp1 = get_group_from_id('C')
    id_grp2 = get_group_from_id('D')
    merge_identity_groups(id_grp1, id_grp2)
    db.session.commit()

    grouping = (
        [
            ['A', 'B'],
            ['C', 'D'],
            [0],  # {AB}
            [1],  # {CD}
        ],
        [
            ('A', Relation.Cites, 'C'),
            ('B', Relation.Cites, 'C'),
            ('D', Relation.Cites, 'A'),
            ('D', Relation.Cites, 'B'),
            # Identity group relations:
            (0, Relation.Cites, 1),  # AB-Cites-CD
            (1, Relation.Cites, 0),  # CD-Cites-AB
            # Version group relations:
            (2, Relation.Cites, 3),  # AB-Cites-CD
            (3, Relation.Cites, 2),  # CD-CItes-AB
        ],
        [
            (4, [0, 1, ]),
            (5, [2, 3, ]),
            (6, [4]),
            (7, [5]),
        ]
    )

    assert_grouping(grouping)
    id_grp1 = get_group_from_id('A').data
    id_grp2 = get_group_from_id('B').data
    assert id_grp1 == id_grp2 and id_grp1.json['Title'] == 'Title of B v2'

    id_grp1 = get_group_from_id('A')
    id_grp2 = get_group_from_id('C')
    merge_identity_groups(id_grp1, id_grp2)
    db.session.commit()

    grouping = (
        [
            ['A', 'B', 'C', 'D'],
            [0],  # {ABCD}
        ],
        [
            ('A', Relation.Cites, 'C'),
            ('B', Relation.Cites, 'C'),
            ('D', Relation.Cites, 'A'),
            ('D', Relation.Cites, 'B'),
            # No group relations for only one identity and one version
        ],
        []  # No relations M2M
    )

    id_grp1 = get_group_from_id('A').data
    id_grp2 = get_group_from_id('B').data
    id_grp3 = get_group_from_id('C').data
    id_grp4 = get_group_from_id('D').data
    # All metadata should be merged to that of the last "D" object
    assert id_grp1 == id_grp2 == id_grp3 == id_grp4 and \
        id_grp1.json['Title'] == 'Title of D v2'
    assert_grouping(grouping)
