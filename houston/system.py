__all__ = ['System']

from typing import List, Dict, FrozenSet, Any, Type
import warnings
import logging

import bugzoo
from bugzoo.client import Client as BugZooClient

from .command import Command
from .configuration import Configuration
from .sandbox import Sandbox
from .state import Variable, State

logger = logging.getLogger(__name__)  # type: logging.Logger
logger.setLevel(logging.DEBUG)


_NAME_TO_SYSTEM_TYPE = {}  # type: Dict[str, Type[System]]


class SystemMeta(type):
    def __new__(mcl,
                cls_name: str,
                bases,  # FIXME
                ns: Dict[str, Any]
                ):
        # is this an abstract class?
        if 'is_abstract' in ns:
            is_abstract = ns['is_abstract']
            if not isinstance(ns['is_abstract'], bool):
                tpl = "Unexpected type for 'is_abstract' property: {}"
                typ = type(ns['is_abstract']).__name__
                msg = "expected 'bool' but was '{}'".format(typ)
                msg = tpl.format(msg)
                raise TypeError(msg)
        else:
            is_abstract = False

        # FIXME create immutable attribute
        ns['is_abstract'] = is_abstract

        if not is_abstract:
            if 'name' not in ns:
                msg = "System class definition is missing 'name' property"
                raise TypeError(msg)
            sys_name = ns['name']
            if not isinstance(sys_name, str):
                msg = "was {} but should be str".format(type(sys_name))
                msg = "Unexpected type for 'name' property: {}".format(msg)
                raise TypeError(msg)
            if sys_name == '':
                msg = "System name must be a non-empty string."
                raise TypeError(msg)

            # FIXME create immutable class attribute
            ns['name'] = sys_name

            if 'state' not in ns:
                msg = "System class definition is missing 'state' property"
                raise TypeError(msg)
            if not issubclass(ns['state'], State):
                typ = ns['state'].__name__
                msg = "was {} but should be a subclass of State".format(typ)
                msg = "Unexpected class for 'state' property: {}".format(msg)
                raise TypeError(msg)

            if 'sandbox' not in ns:
                msg = "System class definition is missing 'sandbox' property"
                raise TypeError(msg)
            if not issubclass(ns['sandbox'], Sandbox):
                typ = ns['sandbox'].__name__
                msg = "was {} but should be a subclass of Sandbox".format(typ)
                msg = "Unexpected class for 'sandbox' property: {}".format(msg)
                raise TypeError(msg)

            if 'commands' not in ns:
                msg = "System class definition is missing 'commands' property"
                raise TypeError(msg)
            if not isinstance(ns['commands'], list) \
               or any(not issubclass(x, Command) for x in ns['commands']):
                msg = "was {} but should be List[Type[Command]]"
                msg = msg.format(ns['commands'])
                msg = "Unexpected type for 'commands' property: {}".format(msg)

            # TODO convert to a frozen dictionary
            ns['commands'] = {c.name: c for c in ns['commands']}

            if 'configuration' not in ns:
                msg = "System class definition is missing 'configuration' property"  # noqa: pycodestyle
                raise TypeError(msg)
            if not issubclass(ns['configuration'], Configuration):
                msg = "was {} but should be a subclass of Configuration"
                msg = msg.format(ns['configuration'].__name__)
                tpl = "Unexpected class for 'configuration' property: {}"
                msg = tpl.format(msg)
                raise TypeError(msg)

        return super().__new__(mcl, cls_name, bases, ns)

    def __init__(cls, cls_name: str, bases, ns: Dict[str, Any]):
        if cls.is_abstract:
            return super().__init__(cls_name, bases, ns)

        # register system type
        if cls.name in _NAME_TO_SYSTEM_TYPE:
            msg = "System already registered under given name: %s"
            msg = msg.format(cls.name)
            raise TypeError(msg)
        _NAME_TO_SYSTEM_TYPE[cls.name] = cls

        return super().__init__(cls_name, bases, ns)


class System(object, metaclass=SystemMeta):
    """
    Instances of the System class are used to provide a description of a
    system-under-test, and to provide an interface for safely interacting
    with the system-under-test in an idempotent manner.
    """
    is_abstract = True

    @staticmethod
    def get_by_name(name: str) -> 'Type[System]':
        """
        Attempts to find the type definition for a system with a given name.

        Raises:
            KeyError: if no system type is registered under the given name.
        """
        return __NAME_TO_SYSTEM_TYPE[name]
