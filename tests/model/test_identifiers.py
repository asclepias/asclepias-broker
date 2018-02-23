"""Test broker model."""
import pytest

from asclepias_broker.datastore import Identifier

from helpers import generate_payloads


@pytest.mark.parametrize(
    ('events', 'result_sets'), [
        ([
            ['C', 'A', 'Cites', 'B', '2018-01-01'],
         ],
         [{'A'}, {'B'}]),
        ([
            ['C', 'A', 'IsIdenticalTo', 'B', '2018-01-01'],
         ],
         [{'A', 'B'}]),
        ([
            ['C', 'A', 'IsIdenticalTo', 'B', '2018-01-01'],
            ['D', 'A', 'IsIdenticalTo', 'B', '2018-01-01'],
         ],
         [{'A'}, {'B'}]),
        ([
            ['C', 'A', 'IsIdenticalTo', 'B', '2018-01-01'],
            ['C', 'B', 'IsIdenticalTo', 'C', '2018-01-01'],
         ],
         [{'A', 'B', 'C'}]),
        # Redundant relationships
        ([
            ['C', 'A', 'IsIdenticalTo', 'B', '2018-01-01'],
            ['C', 'B', 'IsIdenticalTo', 'C', '2018-01-01'],
            ['C', 'C', 'IsIdenticalTo', 'A', '2018-01-01'],
         ],
         [{'A', 'B', 'C'}]),
        # Other relationships
        ([
            ['C', 'A', 'IsIdenticalTo', 'B', '2018-01-01'],
            ['C', 'B', 'IsIdenticalTo', 'C', '2018-01-01'],
            ['C', 'X', 'Cites', 'B', '2018-01-01'],
            ['C', 'A', 'Cites', 'Y', '2018-01-01'],
         ],
         [{'A', 'B', 'C'}, {'X'}, {'Y'}]),
        # With other group of identifier relationships
        ([
            ['C', 'A', 'IsIdenticalTo', 'B', '2018-01-01'],
            ['C', 'B', 'IsIdenticalTo', 'C', '2018-01-01'],
            ['C', 'X', 'Cites', 'Y', '2018-01-01'],
         ],
         [{'A', 'B', 'C'}, {'X'}, {'Y'}]),
        # With irrelevant 'IsIdenticalTo' identifier relationships
        ([
            ['C', 'A', 'IsIdenticalTo', 'B', '2018-01-01'],
            ['C', 'B', 'IsIdenticalTo', 'C', '2018-01-01'],
            ['C', 'X', 'IsIdenticalTo', 'Y', '2018-01-01'],
         ],
         [{'A', 'B', 'C'}, {'X', 'Y'}]),
        ([
            ['C', 'A', 'IsIdenticalTo', 'B', '2018-01-01'],
            ['C', 'B', 'IsIdenticalTo', 'C', '2018-01-01'],
            ['C', 'X', 'IsIdenticalTo', 'Y', '2018-01-01'],
            ['C', 'X', 'IsIdenticalTo', 'Z', '2018-01-01'],
         ],
         [{'A', 'B', 'C'}, {'X', 'Y', 'Z'}]),
        ([
            ['C', 'A', 'IsIdenticalTo', 'B', '2018-01-01'],
            ['C', 'B', 'IsIdenticalTo', 'C', '2018-01-01'],
            ['C', 'X', 'IsIdenticalTo', 'Y', '2018-01-01'],
            ['C', 'X', 'IsIdenticalTo', 'Z', '2018-01-01'],
            ['C', 'Z', 'IsIdenticalTo', 'A', '2018-01-01'],
         ],
         [{'A', 'B', 'C', 'X', 'Y', 'Z'}]),
        ([
            ['C', 'A', 'IsIdenticalTo', 'B', '2018-01-01'],
            ['C', 'B', 'IsIdenticalTo', 'C', '2018-01-01'],
            ['C', 'X', 'IsIdenticalTo', 'Y', '2018-01-01'],
            ['C', 'X', 'IsIdenticalTo', 'Z', '2018-01-01'],
            ['C', 'Z', 'IsIdenticalTo', 'A', '2018-01-01'],
            ['D', 'Z', 'IsIdenticalTo', 'A', '2018-01-01'],
         ],
         [{'A', 'B', 'C'}, {'X', 'Y', 'Z'}]),
    ]
    )
def test_identities(broker, events, result_sets):
    # NOTE: We assume that only on identifier scheme being used so just using
    # identifier values is enough when comparing sets.
    for ev in generate_payloads(events):
        broker.handle_event(ev)

    for rs in result_sets:
        for v in rs:
            id_ = broker.session.query(Identifier).filter_by(value=v).one()
            ids = set(i.value for i in id_.get_identities(broker.session))
            assert ids == rs
