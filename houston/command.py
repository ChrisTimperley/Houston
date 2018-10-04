__all__ = ['Command', 'Parameter', 'CommandOutcome']

from typing import List, Dict, Any, Optional, Type, Generic, \
    TypeVar, Iterator
import random
import logging

import attr

from .specification import Specification
from .configuration import Configuration
from .state import State
from .environment import Environment
from .valueRange import ValueRange

logger = logging.getLogger(__name__)   # type: logging.Logger
logger.setLevel(logging.DEBUG)


T = TypeVar('T')

# contains all command types, indexed by their unique identifiers
_UID_TO_COMMAND_TYPE = {}  # type: Dict[str, Type[Command]]


@attr.s(frozen=True)
class Parameter(Generic[T]):
    name = attr.ib(type=str)
    values = attr.ib(type=ValueRange)

    def generate(self, rng: random.Random) -> T:
        """
        Returns a randomly-generated value for this parameter.
        """
        return self.values.sample(rng)

    @property
    def type(self) -> Type[T]:
        """
        The underlying type of this parameter.
        """
        return self.values.type

    @property
    def _field(self) -> str:
        """
        The name of the field that stores the value of this parameter.
        """
        return "__{}".format(self.name)


class CommandMeta(type):
    def __new__(mcl,
                cls_name: str,
                bases,  # FIXME
                ns: Dict[str, Any]
                ):
        if bases == (object,):
            return super().__new__(mcl, cls_name, bases, ns)

        # build an exception message template
        tpl_err = "failed to build definition for command [{}]: "
        tpl_err = tpl_err.format(cls_name) + "{}"

        # obtain name
        logger.debug("obtaining command name")
        try:
            name_command = ns['name']  # type: str
        except KeyError:
            msg = "missing 'name' field in Command definition"
            raise TypeError(tpl_err.format(msg))

        if not isinstance(name_command, str):
            t = type(name_command)
            msg = "expected 'name' field to be str but was {}".format(t)
            raise TypeError(tpl_err.format(msg))

        if name_command == '':
            msg = "'name' field must not be an empty string"
            raise TypeError(tpl_err.format(msg))
        logger.debug("obtained command name: %s", name_command)

        # build parameters
        logger.debug("building command parameters")
        try:
            params = ns['parameters']  # type: List[Parameter]
        except KeyError:
            msg = "missing 'parameters' field in Command definition"
            raise TypeError(tpl_err.format(msg))

        # FIXME build a FrozenDict
        ns['parameters'] = frozenset(params)

        logger.debug("built command parameters")

        # build specifications
        logger.debug("building specifications")
        try:
            specs = ns['specifications']  # type: List[Specifications]
        except KeyError:
            msg = "missing 'specifications' field in Command definition"
            raise TypeError(tpl_err.format(msg))

        if not (isinstance(specs, list) and all(isinstance(s, Specification) for s in specs)):  # noqa: pycodestyle
            msg = "expected 'specifications' field to be List[Specification]"
            raise TypeError(tpl_err.format(msg))

        if specs is []:
            msg = "all commands must provide at least one Specification"
            raise TypeError(tpl_err.format(msg))

        if len(set(s.name for s in specs)) != len(specs):
            msg = "each specification must be given a unique name"
            raise TypeError(tpl_err.format(msg))

        # TODO type check specs

        # FIXME build a FrozenDict
        ns['specifications'] = list(specs)
        logger.debug("built specifications")

        logger.debug("constructing properties")
        for param in params:
            field = param._field
            getter = lambda self, f=field: getattr(self, f)
            ns[param.name] = property(getter)
        logger.debug("constructed properties")

        return super().__new__(mcl, cls_name, bases, ns)

    def __init__(cls, cls_name: str, bases, ns: Dict[str, Any]):
        if bases == (object,):
            return super().__init__(cls_name, bases, ns)

        # build an exception message template
        tpl_err = "failed to build definition for command [{}]: "
        tpl_err = tpl_err.format(cls_name) + "{}"

        # obtain or generate a unique identifier
        if 'uid' in ns:
            uid = ns['uid']
            if not isinstance(uid, str):
                t = type(uid)
                msg = "expected 'uid' field to be str but was {}".format(t)
                raise TypeError(tpl_err.format(msg))
            logger.debug("using provided UID: %s", uid)
        else:
            uid = '{}.{}'.format(cls.__module__, cls.__qualname__)

        # ensure uid is not an empty string
        if uid == '':
            msg = "'uid' field must not be an empty string"
            raise TypeError(tpl_err.format(msg))

        # convert uid to a read-only property
        ns['uid'] = property(lambda u=uid: u)

        # ensure that uid isn't already in use
        if uid in _UID_TO_COMMAND_TYPE:
            msg = "'uid' already in use [%s]".format(uid)
            raise TypeError(tpl_error.format(msg))

        logger.debug("registering command type [%s] with UID [%s]", cls, uid)
        _UID_TO_COMMAND_TYPE[uid] = cls
        logger.debug("registered command type [%s] with UID [%s]", cls, uid)

        return super().__init__(cls_name, bases, ns)


class Command(object, metaclass=CommandMeta):
    def __init__(self, *args, **kwargs) -> None:
        cls_name = self.__class__.__name__
        params = self.__class__.parameters  # type: FrozenSet[Parameter]

        # were any positional arguments passed to the constructor?
        if args:
            msg = "constructor [{}] accepts no positional arguments but {} {} given"  # noqa: pycodestyle
            msg = msg.format(cls_name,
                             "was" if len(args) == 1 else "were",
                             len(args))
            raise TypeError(msg)

        # set values for each variable
        for p in params:
            try:
                val = kwargs[p.name]
            except KeyError:
                msg = "missing keyword argument [{}] to constructor [{}]"
                msg = msg.format(p.name, cls_name)
                raise TypeError(msg)

            # TODO perform run-time type checking?
            setattr(self, p._field, val)

        # did we pass any unexpected keyword arguments?
        if len(kwargs) > len(params):
            actual_args = set(n for n in kwargs)
            expected_args = set(p.name for p in params)
            unexpected_arguments = list(actual_args - expected_args)
            msg = "unexpected keyword arguments [{}] supplied to constructor [{}]"  # noqa: pycodestyle
            msg = msg.format('; '.join(unexpected_arguments), cls_name)
            raise TypeError(msg)

    def __eq__(self, other: 'Command') -> bool:
        if type(self) != type(other):
            msg = "illegal comparison of commands: [{}] vs. [{}]"
            msg = msg.format(self.uid, other.uid)
            raise Exception(msg)  # FIXME use HoustonException
        for param in self.__class__.parameters:
            if self[param.name] != other[param.name]:
                return False
        return True

    def __getitem__(self, name: str) -> Any:
        # FIXME use frozendict
        try:
            params = self.__class__.parameters
            param = next(p for p in params if p.name == name)
        except StopIteration:
            msg = "no parameter [{}] in command [{}]"
            msg.format(name, self.__class__.__name__)
            raise KeyError(msg)
        return getattr(self, param._field)

    @property
    def uid(self) -> str:
        """
        The UID of the type of this command.
        """
        return self.__class__.uid

    @property
    def name(self) -> str:
        """
        The name of the type of this command.
        """
        return self.__class__.__name__

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> 'Command':
        name_typ = d['type']
        typ = _UID_TO_COMMAND_TYPE[name_typ]  # type: Type[Command]
        params = d['parameters']
        return typ(**params)

    def to_dict(self) -> Dict[str, Any]:
        fields = {
            'type': self.uid,
            'parameters': {}
        }  # type: Dict[str, Any]
        for param in self.__class__.parameters:
            fields['parameters'][param.name] = getattr(self, param._field)
        return fields

    def __repr__(self) -> str:
        fields = self.to_dict()['parameters']
        for (name, val) in fields.items():
            if isinstance(val, float):
                s = "{:.3f}".format(val)
            else:
                s = str(val)
            fields[name] = val
        s = '; '.join(["{}: {}".format(k, v) for (k, v) in fields.items()])
        s = "{}({})".format(self.__class__.__name__, s)
        return s

    def dispatch(self,
                 sandbox: 'Sandbox',
                 state: State,
                 environment: Environment,
                 configuration: Configuration
                 ) -> None:
        """
        Responsible for invoking this command.

        Parameters:
            sandbox: the sandbox for the system under test.
            state: the state of the system immediately prior to the
                call to this method
            environment: a description of the environment in which the
                command is being performed
            configuration: the configuration of the system under test.
        """
        raise NotImplementedError

    def timeout(self,
                state: State,
                environment: Environment,
                config: Configuration
                ) -> float:
        """
        Responsible for calculating the maximum time that this command
        should take to finish its execution.

        Parameters:
            state: the state of the system prior to the execution of the
                command.
            environment: the state of the environment prior to the execution
                of the command.
            configuration: the configuration of the system under test.

        Returns:
            Maximum length of time (in seconds) that the command may take to
            complete its execution.
        """
        spec = self.resolve(state, environment, config)
        return spec.timeout(self, state, environment, config)

    def resolve(self,
                state: State,
                environment: Environment,
                config: Configuration
                ) -> Specification:
        """
        Returns the specification that the system is expected to satisfy when
        completing this command in a given state, environment, and
        configuration.
        """
        for spec in self.__class__.specifications:
            if spec.precondition.is_satisfied(self,
                                              state,
                                              None,
                                              environment,
                                              config):
                return spec
        raise Exception("failed to resolve specification")

    def __iter__(self) -> Iterator[Parameter]:
        yield from self.__class__.parameters


@attr.s(frozen=True)
class CommandOutcome(object):
    """
    Describes the outcome of a command execution in terms of the state of the
    system before and after the execution.
    """
    command = attr.ib(type=Command)
    successful = attr.ib(type=bool)
    start_state = attr.ib(type=State)
    end_state = attr.ib(type=State)
    time_elapsed = attr.ib(type=float)  # FIXME use time delta

    @staticmethod
    def from_json(jsn: Dict[str, Any]) -> 'CommandOutcome':
        return CommandOutcome(Command.from_json(jsn['command']),
                              jsn['successful'],
                              State.from_json(jsn['start_state']),
                              State.from_json(jsn['end_state']),
                              jsn['time_elapsed'])

    def to_json(self) -> Dict[str, Any]:
        return {'command': self.__command.to_json(),
                'successful': self.__successful,
                'start_state': self.start_state.to_json(),
                'end_state': self.end_state.to_json(),
                'time_elapsed': self.__time_elapsed}
