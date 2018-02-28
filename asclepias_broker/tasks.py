"""Utility functions and tasks."""

from .datastore import Relation, Group, GroupType, Identifier2Group, \
    Relationship2GroupRelationship, GroupRelationship, GroupM2M, \
    GroupRelationshipM2M, Identifier, Relationship, GroupMetadata, \
    GroupRelationshipMetadata
import uuid
from sqlalchemy.orm import aliased
from typing import Tuple


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
        # TODO: Delete in a query
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
    # Nothing to do if groups are already merged
    if group_a == group_b:
        return
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

    session.query(Group).filter(Group.id.in_([group_a.id, group_b.id])).delete(
        synchronize_session='fetch')
    # After merging identity groups, we need to merge the version groups


def merge_version_groups(session, group_a: Group, group_b: Group):
    """Merge two Version groups into one."""
    # Nothing to do if groups are already merged
    if group_a == group_b:
        return
    if group_a.type != group_b.type:
        raise ValueError("Cannot merge groups of different type.")
    if group_a.type == GroupType.Identity:
        # Merging Identity groups is done separately
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

    session.query(Group).filter(Group.id.in_([group_a.id, group_b.id])).delete(
        synchronize_session='fetch')
    return merged_group


def get_or_create_groups(
        session, identifier: Identifier) -> Tuple[Group, Group]:
    """Given an Identifier, fetch or create its Identity and Version groups."""
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
    return id2g.group, g2g.group


def get_group_from_id(session, identifier_value, id_type='doi',
                      group_type=GroupType.Identity):
    """Resolve from 'A' to Identity Group of A or to a Version Group of A."""
    id_ = Identifier.get(session, identifier_value, id_type)
    id_grp = id_.id2groups[0].group
    if group_type == GroupType.Identity:
        return id_grp
    else:
        return session.query(GroupM2M).filter_by(subgroup=id_grp).one().group


def add_group_relationship(session, relationship, src_id_grp, tar_id_grp,
                           src_ver_grp, tar_ver_grp):
    """Add a group relationship between corresponding groups."""
    # Add GroupRelationship between Identity groups
    id_grp_rel = GroupRelationship(source=src_id_grp, target=tar_id_grp,
                                   relation=relationship.relation,
                                   type=GroupType.Identity)
    session.add(id_grp_rel)
    rel2grp_rel = Relationship2GroupRelationship(
        relationship=relationship, group_relationship=id_grp_rel)
    session.add(rel2grp_rel)

    # Add GroupRelationship between Version groups
    ver_grp_rel = GroupRelationship(source=src_ver_grp, target=tar_ver_grp,
                                    relation=relationship.relation,
                                    type=GroupType.Version)
    session.add(ver_grp_rel)
    g2g_rel = GroupRelationshipM2M(relationship=ver_grp_rel,
                                   subrelationship=id_grp_rel)
    session.add(g2g_rel)


def update_groups(session, relationship, delete=False):
    """Update groups and related M2M objects for given relationship."""
    src_idg, src_vg = get_or_create_groups(session, relationship.source)
    tar_idg, tar_vg = get_or_create_groups(session, relationship.target)

    if relationship.relation == Relation.IsIdenticalTo:
        merge_identity_groups(session, src_idg, tar_idg)
    elif relationship.relation == Relation.HasVersion:
        merge_version_groups(session, src_vg, tar_vg)
    else: # Relation.Cites, Relation.IsSupplementTo, Relation.IsRelatedTo
        grp_rel = (
            session.query(GroupRelationship)
            .filter(GroupRelationship.source == src_idg,
                    GroupRelationship.target == tar_idg,
                    GroupRelationship.relation == relationship.relation)
            .one_or_none()
        )
        # If GroupRelationship exists, simply add the Relationship M2M entry
        if grp_rel:
            obj = Relationship2GroupRelationship(
                relationship=relationship,
                group_relationship=grp_rel)
            session.add(obj)
        # Otherwise, add the group relationship with propagation
        else:
            add_group_relationship(session, relationship, src_idg, tar_idg,
                                   src_vg, tar_vg)


# TODO: When merging/splitting groups there is some merging/duplicating of
# metadata as well
def update_metadata(session, relationship: Relationship, payload):
    # Get identity groups for source and targer
    src_group = next((id2g.group for id2g in relationship.source.id2groups
                      if id2g.group.type == GroupType.Identity), None)
    trg_group = next((id2g.group for id2g in relationship.target.id2groups
                      if id2g.group.type == GroupType.Identity), None)
    rel_group = session.query(GroupRelationship).filter_by(
        source=src_group, target=trg_group, relation=relationship.relation,
        type=GroupType.Identity).one_or_none()
    if src_group:
        src_metadata = src_group.data or GroupMetadata(group=src_group)
        src_metadata.update(payload['Source'])
    if trg_group:
        trg_metadata = trg_group.data or GroupMetadata(group=trg_group)
        trg_metadata.update(payload['Target'])
    if rel_group:
        rel_metadata = rel_group.data or \
            GroupRelationshipMetadata(group_relationship=rel_group)
        rel_metadata.update(
            {k: v for k, v in payload.items()
             if k in ('LinkPublicationDate', 'LinkProvider')})
    # TODO: Also this is a good place to update the upcoming ES indices
    return (src_group and src_group.data,
            trg_group and trg_group.data,
            rel_group and rel_group.data)
