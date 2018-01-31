"""Utility functions and tasks."""

from .datastore import Relation, Group, GroupType, Identifier2Group, \
    Relationship2GroupRelationship, GroupRelationship, GroupM2M, \
    GroupRelationshipM2M, Identifier
import uuid
from sqlalchemy.orm import aliased


def merge_group_relationships(session, group_a, group_b, merged_group,
        with_identifier_relationships=False):
    """Merge the relationships of merged groups A and B to avoid collisions.

    Groups 'group_a' and 'group_b' will be merged as 'merged_group'.
    This function takes care of moving any duplicate group relations, e.g.:

    If we have 4 relations:
        A Cites X
        B Cites X
        Y Cites A
        Y Cites B
    and we merge groups A and B, we also need to squash the first two and last
    two relations together:

        {AB} Cites X
        Y Cites {AB}

    before we can perform the actual marging of A and B. Otherwise we will
    violate the unique constraint. We do that by removing the duplicate
    relationships (only one of each duplicate pair), so that we can later
    execute and UPDATE.
    """
    # Remove all GroupRelationship objects between groups A and B.
    # Correspnding GroupRelationshipM2M objects will cascade
    (
        session.query(GroupRelationship)
        .filter(
            ((GroupRelationship.source_id == group_a.id) &
             (GroupRelationship.target_id == group_b.id)) |
            ((GroupRelationship.source_id == group_b.id) &
             (GroupRelationship.target_id == group_a.id)))
        .delete(synchronize_session='fetch')
    )

    # We need to execute the same group relation merging twice, first for the
    # 'outgoing' relations ('A Cites X' + 'B Cites X' = 'AB Cites X'), and then
    # for the 'incoming' edges ('Y Cites A' + 'Y Cites B' = 'Y Cites AB').
    # Instead of repeating the code twice, we parametrize it as seen below
    merge_groups_ids = [group_a.id, group_b.id]
    for queried_fk, grouping_fk in [('source_id', 'target_id'),
                                    ('target_id', 'source_id'), ]:
        left_gr = aliased(GroupRelationship, name='left_gr')
        right_gr = aliased(GroupRelationship, name='right_gr')
        left_queried_fk = getattr(left_gr, queried_fk)
        right_queried_fk = getattr(right_gr, queried_fk)
        left_grouping_fk = getattr(left_gr, grouping_fk)
        right_grouping_fk = getattr(right_gr, grouping_fk)

        # 'duplicate_relations' holds GroupRelations, which should be
        # "squashed" after group merging. If we didn't do this, we would
        # violate the UNIQUE constraint
        # Generate 'duplicate_relations' by joining the table with itself
        # by the "grouping_fk" (target_id/source_id)
        duplicate_relations = (
            session.query(left_gr, right_gr)
            .filter(
                left_gr.id < right_gr.id,  # Don't repeat the same pairs
                left_queried_fk.in_(merge_groups_ids),
                right_queried_fk.in_(merge_groups_ids),
                right_queried_fk != left_queried_fk,
                right_gr.relation == left_gr.relation)
            .join(
                right_gr,
                left_grouping_fk == right_grouping_fk)
        )
        del_rel = set()
        for rel_a, rel_b in duplicate_relations:
            kwargs = {
                queried_fk: merged_group.id,
                grouping_fk: getattr(rel_a, grouping_fk),
                'relation': rel_a.relation,
                'id': uuid.uuid4(),
                'type': rel_a.type
            }
            new_grp_rel = GroupRelationship(**kwargs)

            # Delete the duplicate pairs of relationship M2Ms before updating
            delete_duplicate_relationship_m2m(session, rel_a, rel_b)
            session.add(new_grp_rel)
            (
                session.query(GroupRelationshipM2M)
                .filter(GroupRelationshipM2M.relationship_id.in_([rel_a.id, rel_b.id]))
                .update({GroupRelationshipM2M.relationship_id: new_grp_rel.id},
                    synchronize_session='fetch')
            )
            (
                session.query(GroupRelationshipM2M)
                .filter(GroupRelationshipM2M.subrelationship_id.in_([rel_a.id, rel_b.id]))
                .update({GroupRelationshipM2M.subrelationship_id: new_grp_rel.id},
                    synchronize_session='fetch')
            )
            if with_identifier_relationships:
                cls = Relationship2GroupRelationship
                delete_duplicate_relationship_m2m(session, rel_a, rel_b,
                    cls=cls)
                (
                    session.query(cls)
                    .filter(cls.group_relationship_id.in_([rel_a.id, rel_b.id]))
                    .update({cls.group_relationship_id: new_grp_rel.id},
                        synchronize_session='fetch')
                )
            del_rel.add(rel_a.id)
            del_rel.add(rel_b.id)
        # Delete the duplicate relations
        (
            session.query(GroupRelationship)
            .filter(GroupRelationship.id.in_(del_rel))
            .delete(synchronize_session='fetch')
        )

        queried_fk_inst = getattr(GroupRelationship, queried_fk)
        # Update the other non-duplicated relations
        q = (
            session.query(GroupRelationship)
            .filter(queried_fk_inst.in_(merge_groups_ids))
            .update({queried_fk_inst: merged_group.id},
                    synchronize_session='fetch')
        )


def delete_duplicate_relationship_m2m(session, group_a, group_b,
                                      cls=GroupRelationshipM2M):
    """Delete any duplicate relationship M2M objects.

    Deletes any duplicate (unique-constraint violating) M2M objects
    between relationships and group relationships. This step is required
    before merging of two groups.
    """
    if cls == GroupRelationshipM2M:
        queried_fk = 'subrelationship_id'
        grouping_fk = 'relationship_id'
    elif cls == Relationship2GroupRelationship:
        queried_fk = 'group_relationship_id'
        grouping_fk = 'relationship_id'
    else:
        raise ValueError("Parameter 'cls' must be either "
            "'GroupRelationshipM2M' or 'Relationship2GroupRelationship'.")

    for queried_fk, grouping_fk in [(queried_fk, grouping_fk),
                                    (grouping_fk, queried_fk), ]:
        left_gr = aliased(cls, name='left_gr')
        right_gr = aliased(cls, name='right_gr')
        left_queried_fk = getattr(left_gr, queried_fk)
        right_queried_fk = getattr(right_gr, queried_fk)
        left_grouping_fk = getattr(left_gr, grouping_fk)
        right_grouping_fk = getattr(right_gr, grouping_fk)
        merge_groups_ids = [group_a.id, group_b.id]

        duplicate_relations = (
            session.query(left_gr, right_gr)
            .filter(
                # Because we join in the same table by grouping_fk, we will have
                # pairs [(A,B), (B,A)] on the list. We can impose an inequality
                # condition on one FK to reduce this to just one pair [(A,B)]
                left_queried_fk < right_queried_fk,
                left_queried_fk.in_(merge_groups_ids),
                right_queried_fk.in_(merge_groups_ids),
                right_queried_fk != left_queried_fk,
                )
            .join(
                right_gr,
                left_grouping_fk == right_grouping_fk)
        )
        for rel_a, rel_b in duplicate_relations:
            session.delete(rel_a)


def delete_duplicate_group_m2m(session, group_a: Group, group_b: Group):
    """
    Delete any duplicate GroupM2M objects.

    Removes one of each pair of GroupM2M objects for groups A and B.
    """
    cls = GroupM2M
    queried_fk = 'group_id'
    grouping_fk = 'subgroup_id'

    for queried_fk, grouping_fk in [(queried_fk, grouping_fk),
                                    (grouping_fk, queried_fk), ]:
        left_gr = aliased(cls, name='left_gr')
        right_gr = aliased(cls, name='right_gr')
        left_queried_fk = getattr(left_gr, queried_fk)
        right_queried_fk = getattr(right_gr, queried_fk)
        left_grouping_fk = getattr(left_gr, grouping_fk)
        right_grouping_fk = getattr(right_gr, grouping_fk)
        merge_groups_ids = [group_a.id, group_b.id]

        duplicate_relations = (
            session.query(left_gr, right_gr)
            .filter(
                # Because we join in the same table by grouping_fk, we will have
                # pairs [(A,B), (B,A)] on the list. We impose an inequality
                # condition on one FK to reduce this to just one pair [(A,B)]
                left_queried_fk < right_queried_fk,
                left_queried_fk.in_(merge_groups_ids),
                right_queried_fk.in_(merge_groups_ids),
                right_queried_fk != left_queried_fk,
                )
            .join(
                right_gr,
                left_grouping_fk == right_grouping_fk)
        )
        # TODO: Delete in a query
        for rel_a, rel_b in duplicate_relations:
            session.delete(rel_a)


def merge_identity_groups(session, group_a: Group, group_b: Group):
    """Merge two groups of type "Identity".

    Merges the groups together into one group, taking care of migrating
    all group relationships and M2M objects.
    """
    if not (group_a.type == group_b.type == GroupType.Identity):
        raise ValueError("Can only merge Identity groups.")

    # TODO: Should join with Group and filter by Group.type=GroupType.Version
    version_group_a = session.query(GroupM2M).filter_by(
        subgroup=group_a).one().group
    version_group_b = session.query(GroupM2M).filter_by(
        subgroup=group_b).one().group

    merge_version_groups(session, version_group_a, version_group_b)

    merged_group = Group(type=GroupType.Identity, id=uuid.uuid4())
    session.add(merged_group)

    merge_group_relationships(session, group_a, group_b, merged_group,
                              with_identifier_relationships=True)

    (session.query(Identifier2Group)
     .filter(Identifier2Group.group_id.in_([group_a.id, group_b.id]))
     .update({Identifier2Group.group_id: merged_group.id},
             synchronize_session='fetch'))

    # Delete the duplicate GroupM2M entries and update the remaining with
    # the new Group
    delete_duplicate_group_m2m(session, group_a, group_b)
    (session.query(GroupM2M)
     .filter(GroupM2M.subgroup_id.in_([group_a.id, group_b.id]))
     .update({GroupM2M.subgroup_id: merged_group.id},
             synchronize_session='fetch'))

    session.delete(group_a)
    session.delete(group_b)
    # After merging identity groups, we need to merge the version groups


def merge_version_groups(session, group_a: Group, group_b: Group):
    """Merge two Version groups into one."""
    if group_a == group_b:
        return
    if group_a.type != group_b.type:
        raise ValueError("Cannot merge groups of different type.")
    if group_a.type == GroupType.Identity:
        raise ValueError("Cannot merge groups of type 'Identity'.")

    merged_group = Group(type=group_a.type, id=uuid.uuid4())
    session.add(merged_group)

    merge_group_relationships(session, group_a, group_b, merged_group)

    # Delete the duplicate GroupM2M entries and update the remaining with
    # the new Group
    delete_duplicate_group_m2m(session, group_a, group_b)
    (session.query(GroupM2M)
     .filter(GroupM2M.group_id.in_([group_a.id, group_b.id]))
     .update({GroupM2M.group_id: merged_group.id},
             synchronize_session='fetch'))
    (session.query(GroupM2M)
     .filter(GroupM2M.subgroup_id.in_([group_a.id, group_b.id]))
     .update({GroupM2M.subgroup_id: merged_group.id},
             synchronize_session='fetch'))

    session.delete(group_a)
    session.delete(group_b)
    return merged_group


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
        grp = merge_identity_groups(session, src_grp, tar_grp)
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
        grp = merge_version_groups(session, src_ver_grp, tar_ver_grp)
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
    return
    # TODO
    if relationship.relation == Relation.IsIdenticalTo:
        return add_identity(session, relationship)
    elif relationship.relation == Relation.HasVersion:
        return add_version(session, relationship)
    else: # Relation.Cites, Relation.IsSupplementTo, Relation.IsRelatedTo
        return add_group_relationship(session, relationship)
