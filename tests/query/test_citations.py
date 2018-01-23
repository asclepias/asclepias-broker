"""Test citation queries."""
import pytest

from asclepias_broker.datastore import Identifier


def common_items(a, b):
    return [(a[k], b[k]) for k in a.keys() & b.keys()]


TEST_STATES = {
    'no_citations': [
        ['C', 'A', 'IsSupplementTo', 'B', '2018-01-01'],
    ],
    'one_citation': [
        ['C', 'A', 'Cites', 'B', '2018-01-01'],
    ],
    'one_identity': [
        ['C', 'A', 'IsIdenticalTo', 'B', '2018-01-01'],
    ],
    'two_identities': [
        ['C', 'A', 'IsIdenticalTo', 'B', '2018-01-01'],
        ['C', 'B', 'IsIdenticalTo', 'C', '2018-01-01'],
    ],
    'three_identities': [
        ['C', 'A', 'IsIdenticalTo', 'B', '2018-01-01'],
        ['C', 'B', 'IsIdenticalTo', 'C', '2018-01-01'],
        ['C', 'C', 'IsIdenticalTo', 'A', '2018-01-01'],
    ],
    'two_identities_and_other_relationships': [
        ['C', 'A', 'IsIdenticalTo', 'B', '2018-01-01'],
        ['C', 'B', 'IsIdenticalTo', 'C', '2018-01-01'],
        ['C', 'X', 'Cites', 'B', '2018-01-01'],
        ['C', 'A', 'Cites', 'Y', '2018-01-01'],
    ],
    'two_identities_and_other_relationships_2': [
        ['C', 'A', 'IsIdenticalTo', 'B', '2018-01-01'],
        ['C', 'B', 'IsIdenticalTo', 'C', '2018-01-01'],
        ['C', 'X', 'Cites', 'Y', '2018-01-01'],
    ],
    'two_groups_of_identities': [
        ['C', 'A', 'IsIdenticalTo', 'B', '2018-01-01'],
        ['C', 'B', 'IsIdenticalTo', 'C', '2018-01-01'],
        ['C', 'X', 'IsIdenticalTo', 'Y', '2018-01-01'],
    ],
    'two_groups_of_identities2': [
        ['C', 'A', 'IsIdenticalTo', 'B', '2018-01-01'],
        ['C', 'B', 'IsIdenticalTo', 'C', '2018-01-01'],
        ['C', 'X', 'IsIdenticalTo', 'Y', '2018-01-01'],
        ['C', 'X', 'IsIdenticalTo', 'Z', '2018-01-01'],
    ],
    'five_identities': [
        ['C', 'A', 'IsIdenticalTo', 'B', '2018-01-01'],
        ['C', 'B', 'IsIdenticalTo', 'C', '2018-01-01'],
        ['C', 'X', 'IsIdenticalTo', 'Y', '2018-01-01'],
        ['C', 'X', 'IsIdenticalTo', 'Z', '2018-01-01'],
        ['C', 'Z', 'IsIdenticalTo', 'A', '2018-01-01'],
    ],
}


NO_ARGS_TEST_CASES = {
    'no_citations': {'A': set(), 'B': set()},
    'one_citation': {{'B': {'A'}}},
    # 'one_citation': {{'B': {'A'}}},
    # 'one_citation': {{'B': {'A'}}},
    # 'one_citation': {{'B': {'A'}}},
    # 'one_citation': {{'B': {'A'}}},
    # 'one_citation': {{'B': {'A'}}},
}


@pytest.mark.parametrize(
    ('broker', 'results'), common_items(TEST_STATES, NO_ARGS_TEST_CASES),
    indirect=['broker'])
def test_no_args_citations(broker, result_sets):
    for id_value, result in result_sets.items():
        id_ = broker.session.query(Identifier).filter_by(value=id_value).one()
        citations = set(i.value for i in broker.get_citations(id_))
        assert citations == result
