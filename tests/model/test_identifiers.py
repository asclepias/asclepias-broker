# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 CERN.
#
# Asclepias Broker is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Test broker model."""
import pytest
from helpers import generate_payload

from asclepias_broker.core.models import Identifier
from asclepias_broker.events.api import EventAPI


@pytest.mark.parametrize(
    ('events', 'result_sets'), [
        ([
            ['A', 'Cites', 'B'],
         ],
         [{'A'}, {'B'}]),
        ([
            ['A', 'IsIdenticalTo', 'B'],
         ],
         [{'A', 'B'}]),
        ([
            ['A', 'IsIdenticalTo', 'B'],
            ['B', 'IsIdenticalTo', 'C'],
         ],
         [{'A', 'B', 'C'}]),
        # Redundant relationships
        ([
            ['A', 'IsIdenticalTo', 'B'],
            ['B', 'IsIdenticalTo', 'C'],
            ['C', 'IsIdenticalTo', 'A'],
         ],
         [{'A', 'B', 'C'}]),
        # Other relationships
        ([
            ['A', 'IsIdenticalTo', 'B'],
            ['B', 'IsIdenticalTo', 'C'],
            ['X', 'Cites', 'B'],
            ['A', 'Cites', 'Y'],
         ],
         [{'A', 'B', 'C'}, {'X'}, {'Y'}]),
        # With other group of identifier relationships
        ([
            ['A', 'IsIdenticalTo', 'B'],
            ['B', 'IsIdenticalTo', 'C'],
            ['X', 'Cites', 'Y'],
         ],
         [{'A', 'B', 'C'}, {'X'}, {'Y'}]),
        # With irrelevant 'IsIdenticalTo' identifier relationships
        ([
            ['A', 'IsIdenticalTo', 'B'],
            ['B', 'IsIdenticalTo', 'C'],
            ['X', 'IsIdenticalTo', 'Y'],
         ],
         [{'A', 'B', 'C'}, {'X', 'Y'}]),
        ([
            ['A', 'IsIdenticalTo', 'B'],
            ['B', 'IsIdenticalTo', 'C'],
            ['X', 'IsIdenticalTo', 'Y'],
            ['X', 'IsIdenticalTo', 'Z'],
         ],
         [{'A', 'B', 'C'}, {'X', 'Y', 'Z'}]),
        ([
            ['A', 'IsIdenticalTo', 'B'],
            ['B', 'IsIdenticalTo', 'C'],
            ['X', 'IsIdenticalTo', 'Y'],
            ['X', 'IsIdenticalTo', 'Z'],
            ['Z', 'IsIdenticalTo', 'A'],
         ],
         [{'A', 'B', 'C', 'X', 'Y', 'Z'}]),
    ]
    )
def test_identities(events, result_sets, db, es):
    # NOTE: We assume that only on identifier scheme being used so just using
    # identifier values is enough when comparing sets.
    for ev in events:
        EventAPI.handle_event(generate_payload(ev))

    for rs in result_sets:
        for v in rs:
            id_ = Identifier.query.filter_by(value=v).one()
            ids = set(i.value for i in id_.get_identities())
            assert ids == rs
