"""Test broker model."""
import pytest

from asclepias_broker.datastore import Relationship, Relation, Identifier,\
    Group, GroupType, Identifier2Group, GroupM2M, GroupRelationship

from asclepias_broker.tasks import get_or_create_groups, merge_m2m_groups

from helpers import generate_payloads

def _handle_events(broker, evtsrc):
    events = generate_payloads(evtsrc)
    for ev in events:
        broker.handle_event(ev)

def test_simple_id_group_merge(broker2):
    """Test simple ID groups merging."""
    broker = broker2
    sess = broker.session
    evtsrc = [
        ['C', 'A', 'IsIdenticalTo', 'B', '2018-01-01'],
    ]
    _handle_events(broker, evtsrc)
    # {'A', 'B'}
    assert sess.query(Group).count() == 2
    vg = sess.query(Group).filter_by(type=GroupType.Version).one()
    vi = sess.query(Group).filter_by(type=GroupType.Identity).one()
    assert sess.query(Identifier).count() == 2
    assert sess.query(Relationship).count() == 1
    assert sess.query(Identifier2Group).count() == 2
    evtsrc = [
        ['C', 'A', 'IsIdenticalTo', 'C', '2018-01-01'],
    ]
    _handle_events(broker, evtsrc)
    # {'A', 'B', 'C'}
    assert sess.query(Group).count() == 1
    assert sess.query(Identifier).count() == 3
    assert sess.query(Identifier2Group).count() == 3

    evtsrc = [
        ['C', 'D', 'IsIdenticalTo', 'E', '2018-01-01'],
    ]
    _handle_events(broker, evtsrc)
    # {'A', 'B', 'C'}, {'D', 'E'}
    assert sess.query(Group).count() == 2
    assert sess.query(Identifier).count() == 5
    assert sess.query(Identifier2Group).count() == 5

    evtsrc = [
        ['C', 'A', 'IsIdenticalTo', 'D', '2018-01-01'],
    ]
    _handle_events(broker, evtsrc)
    # {'A', 'B', 'C', 'D', 'E'}
    assert sess.query(Group).count() == 1
    assert sess.query(Identifier).count() == 5
    assert sess.query(Identifier2Group).count() == 5


def test_2(broker2):
    broker = broker2
    sess = broker.session
    evtsrc = [
        ['C', 'A', 'Cites', 'B', '2018-01-01'],
    ]
    _handle_events(broker, evtsrc)


def test_get_or_create_groups(broker2):
    """Test creating groups (Identity and Version) for an identifier."""
    s = broker2.session
    id1 = Identifier(value='A', scheme='doi')
    s.add(id1)
    #id2 = Identifier(value='B', scheme='doi')
    #rel = Relationship(source=id1, target=id2, relation=Relation.IsIdenticalTo)
    assert not s.query(Group).count()
    assert not s.query(GroupM2M).count()
    assert not s.query(Identifier2Group).count()
    id2g, g2g = get_or_create_groups(s, id1)
    s.commit()

    def _check_groups(identifier, id2g, g2g):
        assert s.query(Group).count() == 2
        assert s.query(GroupM2M).count() == 1
        assert s.query(Identifier2Group).count() == 1
        idgroup = s.query(Group).filter_by(type=GroupType.Identity).one()
        ver_group = s.query(Group).filter_by(type=GroupType.Version).one()
        assert id2g.identifier == identifier
        assert id2g.group == idgroup
        assert g2g.group == ver_group
        assert g2g.subgroup == idgroup

    _check_groups(id1, id2g, g2g)

    # Fetch the ID again and try to create groups again
    id2 = Identifier.get(s, 'A', 'doi')
    assert id2
    id2g, g2g = get_or_create_groups(s, id1)
    s.commit()

    # Make sure nothing changed
    _check_groups(id2, id2g, g2g)

    # Add a new, separate identifier
    id3 = Identifier(value='B', scheme='doi')
    s.add(id3)
    id2g, g2g = get_or_create_groups(s, id3)

    assert s.query(Group).count() == 4
    assert s.query(GroupM2M).count() == 2
    assert s.query(Identifier2Group).count() == 2

def test_merge_g2g_groups(broker2):
    """Test group merging."""
    s = broker2.session
    id1 = Identifier(value='A', scheme='doi')
    s.add(id1)
    id1_id2g, id1_ver_g2g = get_or_create_groups(s, id1)

    id2 = Identifier(value='B', scheme='doi')
    s.add(id2)
    id2_id2g, id2_ver_g2g = get_or_create_groups(s, id2)

    id3 = Identifier(value='C', scheme='doi')
    s.add(id3)
    id3_id2g, id3_ver_g2g = get_or_create_groups(s, id3)

    id4 = Identifier(value='D', scheme='doi')
    s.add(id4)
    id4_id2g, id4_ver_g2g = get_or_create_groups(s, id4)

    # Group relations should be reduced as such:
    # {C}-Cites-{A}
    # {C}-Cites-{B}
    # {A}-Cites-{D}
    # {B}-Cites-{D}
    #
    # Merge(A,B) -> AB
    #
    # C-Cites-AB
    # AB-Cites-D

    s.add(GroupRelationship(source=id3_ver_g2g.group, target=id1_ver_g2g.group, relation=Relation.Cites))
    s.add(GroupRelationship(source=id3_ver_g2g.group, target=id2_ver_g2g.group, relation=Relation.Cites))
    s.add(GroupRelationship(source=id1_ver_g2g.group, target=id4_ver_g2g.group, relation=Relation.Cites))
    s.add(GroupRelationship(source=id2_ver_g2g.group, target=id4_ver_g2g.group, relation=Relation.Cites))

    # Add checks for GroupRelationshipM2M

    assert s.query(Group).count() == 8
    assert s.query(Group).filter_by(type=GroupType.Version).count() == 4
    assert s.query(GroupM2M).count() == 4
    assert s.query(Identifier2Group).count() == 4
    assert s.query(GroupRelationship).count() == 4

    ver_g2g = merge_m2m_groups(s, id1_ver_g2g.group, id2_ver_g2g.group)
    assert s.query(Group).count() == 7
    assert s.query(Group).filter_by(type=GroupType.Version).count() == 3
    assert s.query(GroupM2M).count() == 4
    assert s.query(Identifier2Group).count() == 4
    assert s.query(GroupRelationship).count() == 2

