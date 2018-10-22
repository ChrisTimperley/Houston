import pytest

from houston.environment import Environment


def test_eq():
    consts = {
        'a': 0,
        'b': 1,
        'c': True
    }
    e1 = Environment(consts)
    e2 = Environment(consts)
    assert e1 == e2
    
    consts['c'] = False
    e3 = Environment(consts)
    assert e1 != e3


def test_hash():
    e1_const = {
        'a': 0,
        'b': 1
    }
    e2_const = {
        'b': 1,
        'a': 0
    }
    e1 = Environment(e1_const)
    e2 = Environment(e2_const)
    e3 = Environment(e1_const)
    e4 = Environment(e2_const)

    assert {e1, e2, e3, e4} == {Environment(e1_const), Environment(e2_const)}
