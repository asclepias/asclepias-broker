# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 CERN.
#
# Asclepias Broker is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Test citation queries."""

import pytest
from helpers import generate_payload

from asclepias_broker.core.models import Identifier
from asclepias_broker.events.api import EventAPI
from asclepias_broker.search.api import RelationshipAPI

TEST_CASES = [
    (
        'no_citations',
        [
            ['A', 'IsSupplementTo', 'B'],
        ],
        {
            'A': [set(), set()],
            'B': [set(), set()],
        }
    ),
    (
        'one_identity',
        [
            ['A', 'IsIdenticalTo', 'B'],
        ],
        {
            'A': [set(), set()],
            'B': [set(), set()],
        }
    ),
    (
        'two_identities',
        [
            ['A', 'IsIdenticalTo', 'B'],
            ['B', 'IsIdenticalTo', 'C'],
        ],
        {
            'A': [set(), set()],
            'B': [set(), set()],
            'C': [set(), set()],
        }
    ),
    (
        'one_citation',
        [
            ['A', 'Cites', 'B'],
        ],
        {
            'A': [set(), set()],
            'B': [{'A'}, {('A', 'B')}],
        }
    ),
    (
        'two_citations',
        [
            ['A', 'Cites', 'B'],
            ['C', 'Cites', 'B'],
        ],
        {
            'A': [set(), set()],
            'B': [{'A', 'C'}, {('A', 'B'), ('C', 'B')}],
            'C': [set(), set()],
        }
    ),
    (
        'one_indirect_citation',
        [
            ['A', 'IsIdenticalTo', 'B'],
            ['C', 'Cites', 'B'],
        ],
        {
            'A': [{'C'}, {('C', 'B')}],
            'B': [{'C'}, {('C', 'B')}],
            'C': [set(), set()],
        }
    ),
    (
        'two_indirect_citations',
        [
            ['A', 'IsIdenticalTo', 'B'],
            ['C', 'IsIdenticalTo', 'A'],
            ['X', 'Cites', 'B'],
            ['Y', 'Cites', 'C'],
        ],
        {
            'A': [{'X', 'Y'}, {('X', 'B'), ('Y', 'C')}],
            'B': [{'X', 'Y'}, {('X', 'B'), ('Y', 'C')}],
            'C': [{'X', 'Y'}, {('X', 'B'), ('Y', 'C')}],
            'X': [set(), set()],
            'Y': [set(), set()],
        }
    ),
    (
        'two_indirect_identical_citations',
        [
            ['A', 'IsIdenticalTo', 'B'],
            ['C', 'IsIdenticalTo', 'A'],
            ['X', 'Cites', 'B'],
            ['Y', 'Cites', 'C'],
            ['Y', 'IsIdenticalTo', 'X'],
        ],
        # NOTE: Since the `expand_target` is not called, this still counts two
        # unique citations.
        {
            'A': [{'X', 'Y'}, {('X', 'B'), ('Y', 'C')}],
            'B': [{'X', 'Y'}, {('X', 'B'), ('Y', 'C')}],
            'C': [{'X', 'Y'}, {('X', 'B'), ('Y', 'C')}],
            'X': [set(), set()],
            'Y': [set(), set()],
        }
    ),
]


@pytest.mark.parametrize(('test_case_name', 'events', 'results'), TEST_CASES)
def test_simple_citations(test_case_name, events, results, db, es):
    """Test simple citation queries."""
    for ev in events:
        EventAPI.handle_event(generate_payload(ev))
    es.indices.refresh()
    for cited_id_value, (citation_result, relation_result) in results.items():
        cited_id = (Identifier.query
                    .filter_by(value=cited_id_value).one())
        citations = set()
        relations = set()
        for citing_id, relation in RelationshipAPI.get_citations(cited_id):
            citations |= {i.value for i in citing_id}
            relations |= {(r.source.value, r.target.value) for r in relation}
        assert citations == citation_result
        assert relations == relation_result


TEST_CASES = [
    (
        'one_citation',
        [
            ['A', 'Cites', 'B'],
        ],
        {
            # 'A': [set(), set()],
            'B': [{'A'}, {('A', 'B')}],
        }
    ),
]


@pytest.mark.parametrize(('test_case_name', 'events', 'results'), TEST_CASES)
def test_grouping_query(test_case_name, events, results, db, es):
    for ev in events:
        EventAPI.handle_event(generate_payload(ev))
    for cited_id_value, _ in results.items():
        pass
        # cited_id = Identifier.query.filter_by(value=cited_id_value).one()
        # TODO: Fix this test
        # ret = RelationshipAPI.get_citations2(cited_id, 'IsCitedBy')
