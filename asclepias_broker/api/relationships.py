# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 CERN.
#
# Asclepias Broker is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

from itertools import groupby

from invenio_db import db

from ..mappings import ObjectDoc
from ..models import Group, GroupRelationship, GroupType, Identifier, \
    Identifier2Group, Relation
from ..schemas.loaders import from_datacite_relation
from .ingestion import get_group_from_id


class RelationshipAPI:

    @classmethod
    def get_relationships(cls, id_: str, scheme: str, relation: str,
                          target_type: str=None, from_: str=None, to: str=None,
                          group_by: str=None, page: int=1, size: int=10):
        src_doc = ObjectDoc.get_by_identifiers([id_])
        rels = {'hits': [], 'total': 0}
        if src_doc:
            rel_hits = src_doc.relationships(
                relation, from_=from_, to=to, page=page, size=size)
            if rel_hits:
                rels['total'] = rel_hits.total
                histories = {r._source.TargetID: [h.to_dict()
                                                  for h in r._source.History]
                             for r in rel_hits}
                if target_type:
                    target_objects = (
                        ObjectDoc.search()
                        .query('ids', values=histories.keys())
                        .query('term', **{'Type.Name': target_type})).scan()
                else:
                    target_objects = ObjectDoc.mget(histories.keys())
                rels['hits'] = [
                    {'Target': o.to_dict(), 'LinkHistory': histories[o._id]}
                    for o in target_objects]
        return src_doc, rels

    @classmethod
    def print_citations(self, pid_value):
        id_A = Identifier.query.filter_by(scheme='DOI', value=pid_value).one()
        ids = id_A.get_identities()
        full_c = self.get_citations(id_A, with_parents=True, with_siblings=True, expand_target=True)
        from pprint import pprint
        pprint(full_c)


    @classmethod
    def get_citations(self, identifier, with_parents=False, with_siblings=False, expand_target=False):
        # At the beginning, frontier is just identities
        frontier = identifier.get_identities()
        frontier_rel = set()
        # Expand with parents
        if with_parents or with_siblings:
            parents_rel = set(sum([iden.get_parents(Relation.HasVersion, as_relation=True)
                                    for iden in frontier], []))
            iden_parents = [item.source for item in parents_rel]
            iden_parents = set(sum([p.get_identities() for p in iden_parents], []))
            if with_parents:
                frontier_rel |= parents_rel
                frontier += iden_parents
        # Expand with siblings
        if with_siblings:
            children_rel = set(sum([p.get_children(Relation.HasVersion, as_relation=True)
                                    for p in iden_parents], []))
            frontier_rel |= children_rel
            par_children = [item.target for item in children_rel]
            par_children = set(sum([c.get_identities() for c in par_children], []))
            frontier += par_children
        frontier = set(frontier)
        # frontier contains all identifiers which directly cite the resource
        citations = set(sum([iden.get_parents(Relation.Cites, as_relation=True) for iden in frontier], []))
        # Expand it to identical identifiers and group them if they repeat
        expanded_sources = [c.source.get_identities() for c in citations]
        zipped = sorted(zip(expanded_sources, citations), key=lambda x: [xi.value for xi in x[0]])
        aggregated_citations = [(k, list(vi for _, vi in v)) for k, v in groupby(zipped, key=lambda x: x[0])]
        frontier_rel = list(frontier_rel) + list(set(sum([item._get_identities(as_relation=True) for item in frontier], [])))
        if expand_target:
            aggregated_citations = [(list(frontier), frontier_rel)] + aggregated_citations
        return aggregated_citations

    @classmethod
    def get_citations2(self, identifier, relation: str, grouping_type=GroupType.Identity):

        grp = get_group_from_id(identifier.value, identifier.scheme,
                                group_type=grouping_type)

        relation, inverse = from_datacite_relation(relation)
        object_fk = GroupRelationship.source_id
        target_fk = GroupRelationship.target_id
        if inverse:
            object_fk, target_fk = target_fk, object_fk

        res = (
            db.session.query(GroupRelationship, Group, Identifier)  # TODO: +join by metadatas
            .filter(object_fk == grp.id,
                    GroupRelationship.relation == relation)
            .join(Group, target_fk == Group.id)
            .join(Identifier2Group, target_fk == Identifier2Group.group_id)
            .join(Identifier, Identifier2Group.identifier_id == Identifier.id)
            .order_by(Group.id)
            .all()
        )
        from itertools import groupby
        result = [(k, list(v)) for k, v in groupby(res, key=lambda x: x[1])]
        return result
