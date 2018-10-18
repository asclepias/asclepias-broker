# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 CERN.
#
# Asclepias Broker is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
"""Search views."""
import json

from flask import Blueprint, abort, request
from invenio_oauth2server import require_api_auth

from asclepias_broker.search.api import RelationshipAPI

from ..core.models import Identifier

blueprint = Blueprint('asclepias_search', __name__)


@blueprint.route('/citations/<path:pid_value>')
@require_api_auth()
def citations(pid_value):
    """Renders all citations for an identifier."""
    identifier = Identifier.query.filter_by(
        scheme='doi', value=pid_value).first()
    if not identifier:
        return abort(404)
    else:
        citations = RelationshipAPI.get_citations(
            identifier, with_parents=True, with_siblings=True,
            expand_target=True)
        target = citations[0]
        citations = citations[1:]

        return json.dumps({'target': _target_to_json(target),
                           'citations': _citations_to_json(citations)})


def _citations_to_json(citations):
    citations_json = []
    for c in citations:
        ids, rels = c
        PIDs = []
        for id in ids:
            PIDs.append(id.value)
        citing_relations = []
        for rel in rels:
            citing_relations.append(str(rel))
        citations_json.append({'PIDs': PIDs,
                               'citingRelations': citing_relations})
    return citations_json


def _target_to_json(target):
    t_ids, t_rels = target
    equivalent_PIDs = []
    for id in t_ids:
        equivalent_PIDs.append(id.value)
    equivalence_relations = []
    for rel in t_rels:
        equivalence_relations.append(str(rel)),
    target_json = {
        'equivalentPIDs': equivalent_PIDs,
        'equivalenceRelations': equivalence_relations
    }
    return target_json


@blueprint.route('/db-relationships')
@require_api_auth()
def relationships():
    """Renders relationships for an identifiers from DB."""
    id_ = request.values['id']
    scheme = request.values['scheme']
    relation = request.values['relation']
    grouping = request.values.get('grouping')  # optional parameter

    identifier = Identifier.query.filter_by(scheme=scheme, value=id_).first()
    if not identifier:
        return abort(404)
    else:
        if grouping:
            citations = RelationshipAPI\
                .get_citations2(identifier, relation, grouping)
        else:
            citations = RelationshipAPI.get_citations2(identifier, relation)

        citations_ids = []
        for gid, citlist in citations:
            for grouprel, group, id in citlist:
                citations_ids.append(id.value)

        return json.dumps({'target': identifier.value,
                           'citations': citations_ids})
