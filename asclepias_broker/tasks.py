from .datastore import Relation, Group, GroupType, Identifier2Group, Relationship2GroupRelationship, GroupRelationship, GroupM2M, GroupRelationshipM2M, Identifier
import uuid

def merge_id_groups(session, group_a, group_b):
    grp = Group(type=GroupType.Identity, id=uuid.uuid4())
    session.add(grp)

    idgroups = session.query(Identifier2Group).filter(
        Identifier2Group.group_id.in_([group_a.id, group_b.id]))

    idgroups.update({Identifier2Group.group_id: grp.id},
                    synchronize_session='fetch')

    supergroups = session.query(GroupM2M).filter(
        GroupM2M.subgroup_id.in_([group_a.id, group_b.id]))

    supergroups.update({GroupM2M.subgroup_id: grp.id},
            synchronize_session='fetch')

    session.delete(group_a)
    session.delete(group_b)
    # Same for GroupRelationship (deduplicate)
    # and GroupM2M (deduplicate)


def merge_m2m_groups(session, group_a, group_b):
    assert group_a.type == group_b.type
    if group_a == group_b:
        return

    grp = Group(type=group_a.type, id=uuid.uuid4())
    session.add(grp)

    # Update all M2M group definitions with the new group
    updated = (
        session.query(GroupM2M)
        .filter(GroupM2M.group_id.in_([group_a.id, group_b.id]))
        .update({GroupM2M.group_id: grp.id},
                synchronize_session='fetch')
    )

    updated = (
        session.query(GroupM2M)
        .filter(GroupM2M.subgroup_id.in_([group_a.id, group_b.id]))
        .update({GroupM2M.subgroup_id: grp.id},
                synchronize_session='fetch')
    )

    updated = (
        session.query(GroupM2M)
        .filter(GroupM2M.subgroup_id.in_([group_a.id, group_b.id]))
        .update({GroupM2M.subgroup_id: grp.id},
                synchronize_session='fetch')
    )
    session.delete(group_a)
    session.delete(group_b)
    return grp
    # GroupRelationship (deduplicate)
    # Same for GroupRelationshipM2M (deduplicate)

def get_or_create_groups(session, identifier: Identifier):
    """Get Identity and Version groups for an identifier.

    If groups do not exist, creates them. Returns a pair of group belongings.
    """

    id2g = session.query(Identifier2Group).filter(
        Identifier2Group.identifier==identifier).one_or_none()
    if not id2g:
        group = Group(type=GroupType.Identity, id=uuid.uuid4())
        session.add(group)
        id2g = Identifier2Group(identifier=identifier, group=group)
        session.add(id2g)
    g2g = (session.query(GroupM2M)
           .join(Group, GroupM2M.group_id == Group.id)
           .filter(GroupM2M.subgroup==id2g.group,
                   Group.type==GroupType.Version)
           .one_or_none())
    if not g2g:
        group = Group(type=GroupType.Version, id=uuid.uuid4())
        session.add(group)
        g2g = GroupM2M(group=group, subgroup=id2g.group)
        session.add(g2g)
    return id2g, g2g

def add_identifier_to_group(session, identifier, group=None):
    """If 'group' is None creates a new Group object."""
    if not group:
        # TODO: can probably skip id=uuid.uuid4()
        group = Group(type=GroupType.Identity, id=uuid.uuid4())
        session.add(group)
    id2g = Identifier2Group(identifier=identifier, group=group)
    session.add(id2g)
    return id2g


def add_group_to_group(session, subgroup, supergroup=None, supergroup_type=None):
    if not supergroup:
        # TODO: can probably skip id=uuid.uuid4()
        supergroup = Group(type=supergroup_type, id=uuid.uuid4())
        session.add(supergroup)
    groupm2m = GroupM2M(group=supergroup, subgroup=subgroup)
    session.add(groupm2m)
    return groupm2m


def add_id_group_relationship(session, relationship):
    src_grp = session.query(Group).join(
        Identifier2Group, Identifier2Group.group_id == Group.id).filter(
        Identifier2Group.identifier_id == relationship.source_id).one_or_none()
    tar_grp = session.query(Group).join(
        Identifier2Group, Identifier2Group.group_id == Group.id).filter(
        Identifier2Group.identifier_id == relationship.target_id).one_or_none()
    if not src_grp:
        src_grp = add_identifier_to_group(session, relationship.source).group
    if not tar_grp:
        tar_grp = add_identifier_to_group(session, relationship.target).group
    kwargs = dict(source=src_grp, target=tar_grp,
                  relation=relationship.relation,
                  type=GroupType.Identity)
    grp_rel = session.query(GroupRelationship).filter_by(**kwargs).one_or_none()
    if not grp_rel:
        grp_rel = GroupRelationship(**kwargs)
        session.add(grp_rel)
    return grp_rel

def add_supergroup_relationship(session, relationship, supergroup_type):
    src_sup_grp = session.query(Group).join(
        GroupM2M, GroupM2M.group_id == Group.id).filter(
        Group.type == supergroup_type,
        GroupM2M.subgroup_id == relationship.source_id).one_or_none()
    tar_sup_grp = session.query(Group).join(
        GroupM2M, GroupM2M.group_id == Group.id).filter(
        Group.type == supergroup_type,
        GroupM2M.subgroup_id == relationship.target_id).one_or_none()

    if not src_sup_grp:
        src_sup_g2g = add_group_to_group(session, relationship.source,
                                         supergroup_type=supergroup_type)
    if not tar_sup_grp:
        tar_sup_g2g = add_group_to_group(session, relationship.target,
                                         supergroup_type=supergroup_type)

def add_group_relationship(session, relationship):
    # GropuRelationship between Identity groups
    id_rel = add_id_group_relationship(session, relationship)
    ver_rel = add_supergroup_relationship(session, id_rel, GroupType.Version)
    return ver_rel

def add_identity(session, relationship):
    src_grp = session.query(Group).join(
        Identifier2Group, Identifier2Group.group_id == Group.id).filter(
        Identifier2Group.identifier_id == relationship.source_id).one_or_none()

    tar_grp = session.query(Group).join(
        Identifier2Group, Identifier2Group.group_id == Group.id).filter(
        Identifier2Group.identifier_id == relationship.target_id).one_or_none()
    if src_grp and tar_grp:
        grp = merge_id_groups(session, src_grp, tar_grp)
    elif src_grp:
        tar2g = add_identifier_to_group(
            session, relationship.target, group=src_grp)
        grp = tar2g.group
    elif tar_grp:
        src2g = add_identifier_to_group(
            session, relationship.source, group=tar_grp)
        grp = src2g.group
    else:
        grp = Group(type=GroupType.Identity)
        src2g = add_identifier_to_group(session, relationship.source, group=grp)
        tar2g = add_identifier_to_group(session, relationship.target, group=grp)
    return grp

def add_version(session, relationship):
    id_grp_rel = add_id_group_relationship(session, relationship)

    src_ver_grp = session.query(Group).join(
        GroupM2M, GroupM2M.group_id == Group.id).filter(
        Group.type == GroupType.Version,
        GroupM2M.subgroup_id == id_grp_rel.source_id).one_or_none()
    tar_ver_grp = session.query(Group).join(
        GroupM2M, GroupM2M.group_id == Group.id).filter(
        Group.type == GroupType.Version,
        GroupM2M.subgroup_id == id_grp_rel.target_id).one_or_none()
    if src_ver_grp and tar_ver_grp:
        grp = merge_m2m_groups(session, src_ver_grp, tar_ver_grp)
    elif src_ver_grp:
        tar_g2g = add_group_to_group(
            session, id_grp_rel.source, supergroup=src_ver_grp)
        grp = tar_g2g.group
    elif tar_ver_grp:
        src_g2g = add_group_to_group(
            session, id_grp_rel.target, supergroup=tar_ver_grp)
        grp = src_g2g.group
    else:
        grp = Group(type=GroupType.Version)
        add_group_to_group(session, grp, id_grp_rel.source)
        add_group_to_group(session, grp, id_grp_rel.target)
    return grp

def update_groups(session, relationship, delete=False):
    if relationship.relation == Relation.IsIdenticalTo:
        return add_identity(session, relationship)
    elif relationship.relation == Relation.HasVersion:
        return add_version(session, relationship)
    else: # Relation.Cites, Relation.IsSupplementTo, Relation.IsRelatedTo
        return add_group_relationship(session, relationship)
