# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 CERN.
#
# Asclepias Broker is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Metadata functions."""

from ..core.models import Relation, Relationship
from ..graph.models import GroupRelationship, GroupType
from .models import GroupMetadata, GroupRelationshipMetadata


# TODO: When merging/splitting groups there is some merging/duplicating of
# metadata as well
def update_metadata(relationship: Relationship, payload):
    """Updates the metadata of the source, target and relationship groups."""
    # Get identity groups for source and targer
    # TODO: Do something for this case?
    if relationship.relation == Relation.IsIdenticalTo:
        return
    src_group = next((id2g.group for id2g in relationship.source.id2groups
                      if id2g.group.type == GroupType.Identity), None)
    trg_group = next((id2g.group for id2g in relationship.target.id2groups
                      if id2g.group.type == GroupType.Identity), None)
    rel_group = GroupRelationship.query.filter_by(
        source=src_group, target=trg_group, relation=relationship.relation,
        type=GroupType.Identity).one_or_none()
    if src_group:
        src_metadata = src_group.data or GroupMetadata(group_id=src_group.id)
        src_metadata.update(payload['Source'])
    if trg_group:
        trg_metadata = trg_group.data or GroupMetadata(group_id=trg_group.id)
        trg_metadata.update(payload['Target'])
    if rel_group:
        rel_metadata = rel_group.data or \
            GroupRelationshipMetadata(group_relationship_id=rel_group.id)
        rel_metadata.update(
            {k: v for k, v in payload.items()
             if k in ('LinkPublicationDate', 'LinkProvider')})
