__all__ = ['State', 'var', 'Variable']

from typing import Dict, Any, Optional, Union, TypeVar, Generic, Type, \
    Callable, FrozenSet, Iterator
import logging
import copy
import json
import math

import attr

logger = logging.getLogger(__name__)  # type: logging.Logger
logger.setLevel(logging.DEBUG)


K = TypeVar('K')


class Variable(object):
    def __init__(self,
                 name: str,
                 typ: Type,
                 getter,  # FIXME add annotation
                 noise: Optional[Union[int, float]] = None
                 ) -> None:
        """
        Constructs a new state variable

        Parameters:
            name: the name of this variable.
            typ: the type of this variable.
            getter: a lambda function, used to obtain the value of this
                variable.
            noise: the inherent level of noise when measuring this variable.
        """
        assert noise is None or noise >= 0
        self.__name = name
        self.__typ = typ
        self.__getter = getter
        self.__noise = noise

    @property
    def typ(self) -> Type:
        return self.__typ

    @property
    def is_noisy(self) -> bool:
        return self.__noise is not None

    @property
    def noise(self) -> Optional[Union[int, float]]:
        """
        The inherent level of noise that is to be expected when measuring
        this variable. If no noise is expected, None is returned.
        """
        return self.__noise

    @property
    def _field(self) -> str:
        """
        The name of the field used to store the value of this variable.
        """
        return "__{}".format(self.__name)

    @property
    def name(self) -> str:
        return self.__name

    def eq(self, x, y) -> bool:
        """
        Determines whether two measurements of this state variable are
        considered to be equal.
        """
        if not self.is_noisy:
            return x == y

        d = math.fabs(x - y)
        return d <= self.__noise

    def neq(self, x, y) -> bool:
        """
        Determines whether two measurements of this state variable are not
        considered to be equal.
        """
        return not self.eq(x, y)

    def gt(self, x, y) -> bool:
        return x > y

    def lt(self, x, y) -> bool:
        return x < y

    def leq(self, x, y) -> bool:
        return not self.gt(x, y)

    def geq(self, x, y) -> bool:
        return not self.lt(x, y)

    def read(self, sandbox):
        """
        Inspects the current state of this system variable
        """
        return self.__getter(sandbox)


@attr.s(frozen=True)
class VariableBuilder(Generic[K]):
    typ = attr.ib(type=Type[K])
    getter = attr.ib(type=Callable[['Sandbox'], K])
    noise = attr.ib(type=Optional[Union[int, float]])

    def build(self, name: str) -> Variable:
        return Variable(name, self.typ, self.getter, self.noise)


def var(typ: Type,
        getter: Callable[['Sandbox'], K],
        noise: Optional[Union[int, float]] = None
        ) -> VariableBuilder:
    return VariableBuilder(typ, getter, noise)


class StateMeta(type):
    def __new__(mcl,
                cls_name: str,
                bases,  # FIXME
                ns: Dict[str, Any]
                ):
        # collect and build variable definitions
        variable_builders = {}  # type: Dict[str, VariableBuilder]
        for name in ns:
            if isinstance(ns[name], VariableBuilder):
                logger.debug("found variable: %s", name)
                variable_builders[name] = ns[name]
        logger.debug("building variables")
        variables = frozenset(
            b.build(name) for (name, b) in variable_builders.items()
        )  # type: FrozenSet[Variable]
        logger.debug("built variables: %s", variables)

        logger.debug("storing variables in variables property")
        ns['variables'] = variables
        logger.debug("stored variables in variables property")

        logger.debug("constructing properties")
        for variable in variables:
            field = variable._field
            getter = lambda self, f=field: getattr(self, f)
            ns[variable.name] = property(getter)
        logger.debug("constructed properties")

        return super().__new__(mcl, cls_name, bases, ns)


class State(object, metaclass=StateMeta):
    """
    Describes the state of the system at a given moment in time, in terms of
    its internal and external variables.
    """
    @classmethod
    def from_file(cls: Type['State'], fn: str) -> 'State':
        """
        Constructs a system state from a given file, containing a JSON-based
        description of its contents.
        """
        with open(fn, "r") as f:
            jsn = json.load(f)
        return cls.from_json(jsn)

    @classmethod
    def from_dict(cls: Type['State'], d: Dict[str, Any]) -> 'State':
        return cls(**d)

    def __init__(self, *args, **kwargs) -> None:
        cls_name = self.__class__.__name__
        variables = self.__class__.variables  # type: FrozenSet[Variable]

        try:
            self.__time_offset = kwargs['time_offset']
        except KeyError:
            msg = "missing keyword argument [time_offset] to constructor [{}]"
            msg = msg.format(cls_name)
            raise TypeError(msg)

        # were any positional arguments passed to the constructor?
        if args:
            msg = "constructor [{}] accepts no positional arguments but {} {} given"  # noqa: pycodestyle
            msg = msg.format(cls_name,
                             "was" if len(args) == 1 else "were",
                             len(args))
            raise TypeError(msg)

        # set values for each variable
        for v in variables:
            try:
                val = kwargs[v.name]
            except KeyError:
                msg = "missing keyword argument [{}] to constructor [{}]"
                msg = msg.format(v.name, cls_name)
                raise TypeError(msg)

            # TODO perform run-time type checking?

            setattr(self, v._field, val)

        # did we pass any unexpected keyword arguments?
        if len(kwargs) > len(variables) + 1:
            actual_args = set(n for n in kwargs)
            expected_args = \
                set(v.name for v in variables) | {'time_offset'}
            unexpected_arguments = list(actual_args - expected_args)
            msg = "unexpected keyword arguments [{}] supplied to constructor [{}]"  # noqa: pycodestyle
            msg = msg.format('; '.join(unexpected_arguments), cls_name)
            raise TypeError(msg)

    @property
    def time_offset(self) -> float:
        return self.__time_offset

    def equiv(self, other: 'State') -> bool:
        if type(self) != type(other):
            msg = "illegal comparison of states: [{}] vs. [{}]"
            msg = msg.format(self.__class__.__name__, state.__class__.__name__)
            raise Exception(msg)  # FIXME use HoustonException
        for v in self.__class__.variables:
            if self.__dict__[v._field] != other.__dict__[v._field]:
                return False
        return True

    def exact(self, other: 'State') -> bool:
        return self.equiv(other) and self.time_offset == other.time_offset

    __eq__ = exact

    def __hash__(self) -> int:
        all_vars = (self.time_offset,)
        all_vars += tuple(self[v.name] for v in self.__class__.variables)
        return hash(all_vars)

    def __getitem__(self, name: str) -> Any:
        # FIXME use frozendict
        try:
            variables = self.__class__.variables
            var = next(v for v in variables if v.name == name)
        except StopIteration:
            msg = "no variable [{}] in state [{}]"
            msg.format(name, self.__class__.__name__)
            raise KeyError(msg)
        return getattr(self, var._field)

    def to_dict(self) -> Dict[str, Any]:
        fields = {}  # type: Dict[str, Any]
        fields['time_offset'] = self.__time_offset
        for var in self.__class__.variables:
            fields[var.name] = getattr(self, var._field)
        return fields

    def __repr__(self) -> str:
        fields = self.to_json()
        for (name, val) in fields.items():
            if isinstance(val, float):
                s = "{:.3f}".format(val)
            else:
                s = str(val)
            fields[name] = val
        s = '; '.join(["{}: {}".format(k, v) for (k, v) in fields.items()])
        s = "{}({})".format(self.__class__.__name__, s)
        return s

    def __iter__(self) -> Iterator[Variable]:
        yield from self.__class__.variables
