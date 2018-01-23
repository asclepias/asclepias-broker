"""Test broker model."""
import pytest

from asclepias_broker.datastore import Identifier


@pytest.mark.parametrize(
    ('broker', 'result'), [
        ([
            ['C', '10.1234/A', 'Cites', '10.1234/B', '2018-01-01'],
         ],
         {'10.1234/A'}),
        ([
            ['C', '10.1234/A', 'IsIdenticalTo', '10.1234/B', '2018-01-01'],
         ],
         {'10.1234/A', '10.1234/B'}),
        ([
            ['C', '10.1234/A', 'IsIdenticalTo', '10.1234/B', '2018-01-01'],
            ['C', '10.1234/B', 'IsIdenticalTo', '10.1234/C', '2018-01-01'],
         ],
         {'10.1234/A', '10.1234/B', '10.1234/C'}),
        # With irrelevant identifier relationships
        ([
            ['C', '10.1234/A', 'IsIdenticalTo', '10.1234/B', '2018-01-01'],
            ['C', '10.1234/B', 'IsIdenticalTo', '10.1234/C', '2018-01-01'],
            ['C', '10.1234/X', 'Cites', '10.1234/Y', '2018-01-01'],
         ],
         {'10.1234/A', '10.1234/B', '10.1234/C'}),
        # With irrelevant 'IsIdenticalTo' identifier relationships
        ([
            ['C', '10.1234/A', 'IsIdenticalTo', '10.1234/B', '2018-01-01'],
            ['C', '10.1234/B', 'IsIdenticalTo', '10.1234/C', '2018-01-01'],
            ['C', '10.1234/X', 'IsIdenticalTo', '10.1234/Y', '2018-01-01'],
         ],
         {'10.1234/A', '10.1234/B', '10.1234/C'}),
    ],
    indirect=['broker'])
def test_identities(broker, result):
    # NOTE: We assume that only on identifier scheme being used so just using
    # identifier values is enough when comparing sets.
    for v in result:
        id_ = broker.session.query(Identifier).filter_by(value=v).one()
        identities = set(i.value for i in id_.get_identities(broker.session))
        assert identities == result
