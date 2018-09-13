import pytest

from houston.state import State, var


def test_variable_construction():
    class S(State):
        foo = var(float, lambda c: 0.1)
    assert set(v.name for v in S.variables) == {'foo'}


def test_constructor():
    class S(State):
        foo = var(float, lambda c: 0.1)

    state = S(foo=0.1, time_offset=30.0)
    assert state.foo == 0.1
    assert state.time_offset == 30.0

    with pytest.raises(TypeError, message="expected TypeError (no arguments)"):
        assert S()
    with pytest.raises(TypeError, message="expected TypeError (missing time_offset)"):
        assert S(foo=0.1)
    with pytest.raises(TypeError, message="expected TypeError (missing foo)"):
        assert S(time_offset=30.0)
    with pytest.raises(TypeError, message="expected TypeError (erroneous property 'bar')"):
        assert S(foo=0.1, bar=1.0, time_offset=30.0)

    class S(State):
        foo = var(int, lambda c: 0)
        bar = var(int, lambda c: 0)

    state = S(foo=0, bar=1, time_offset=0.0)
    assert state.foo == 0
    assert state.bar == 1
    assert state.time_offset == 0.0


def test_is_frozen():
    class S(State):
        foo = var(int, lambda c: 0)
        bar = var(int, lambda c: 0)

    state = S(foo=0, bar=0, time_offset=0.0)
    with pytest.raises(AttributeError, message="expected AttributeError (can't set time_offset)"):
        state.time_offset = 500.0

    with pytest.raises(AttributeError, message="expected AttributeError (can't set foo)"):
        state.foo = 10


def test_eq():
    class S(State):
        foo = var(int, lambda c: 0)
        bar = var(int, lambda c: 0)

    class Y(State):
        foo = var(int, lambda c: 0)
        bar = var(int, lambda c: 0)

    assert S(foo=1, bar=2, time_offset=0.0) == S(foo=1, bar=2, time_offset=0.0)
    assert S(foo=1, bar=2, time_offset=0.0) != S(foo=1, bar=2, time_offset=1.0)
    assert S(foo=1, bar=2, time_offset=0.0) != S(foo=1, bar=3, time_offset=0.0)

    with pytest.raises(Exception, message="expected Exception (states have different parent classes)"):
        assert S(foo=1, bar=2, time_offset=0.0) == Y(foo=1, bar=2, time_offset=0.0)


def test_to_and_from_json():
    class S(State):
        foo = var(int, lambda c: 0)
        bar = var(int, lambda c: 0)

    state = S(foo=1, bar=2, time_offset=0.0)
    jsn = {'foo': 1, 'bar': 2, 'time_offset': 0.0}
    assert state.to_json() == jsn
    assert S.from_json(jsn) == state