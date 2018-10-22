import pytest

from houston.configuration import Configuration, option


def test_option_construction():
    class X(Configuration):
        foo = option(int)
    assert set(o.name for o in X.options) == {'foo'}


def test_constructor():
    class X(Configuration):
        foo = option(int)

    conf = X(foo=0)
    assert conf.foo == 0

    with pytest.raises(TypeError, message="expected TypeError (no arguments)"):
        assert X()
    with pytest.raises(TypeError, message="expected TypeError (positional arguments are disallowed)"):
        assert X(0)
    with pytest.raises(TypeError, message="expected TypeError (erroneous property 'bar')"):
        assert X(foo=0, bar=1)

    class X(Configuration):
        foo = option(int)
        bar = option(int)

    conf = X(foo=0, bar=1)
    assert conf.foo == 0
    assert conf.bar == 1


def test_hash():
    class X(Configuration):
        foo = option(int)
    class Y(Configuration):
        foo = option(int)

    c1 = X(foo=0)
    c2 = X(foo=1)
    c3 = X(foo=0)
    c4 = X(foo=1)

    s = {c1, c2, c3, c4}
    assert s == {X(foo=0), X(foo=1)}

    c5 = Y(foo=0)
    assert len({c1, c5}) == 2
    with pytest.raises(Exception):
        assert c1 != c5



def test_is_frozen():
    class X(Configuration):
        foo = option(int)
    conf = X(foo=0)
    with pytest.raises(AttributeError, message="expected AttributeError (can't set foo)"):
        conf.foo = 10


def test_eq():
    class X(Configuration):
        foo = option(int)
        bar = option(int)

    class Y(Configuration):
        foo = option(int)
        bar = option(int)

    assert X(foo=1, bar=2) == X(foo=1, bar=2)
    assert X(foo=1, bar=2) != X(foo=2, bar=2)
    assert X(foo=1, bar=2) != X(foo=1, bar=1)

    with pytest.raises(Exception, message="expected Exception (confs have different parent classes)"):
        assert X(foo=1, bar=2) == Y(foo=1, bar=2)


def test_to_and_from_dict():
    class X(Configuration):
        foo = option(int)
        bar = option(int)

    conf = X(foo=1, bar=2)
    jsn = {'foo': 1, 'bar': 2}
    assert conf.to_dict() == jsn
    assert X.from_dict(jsn) == conf
