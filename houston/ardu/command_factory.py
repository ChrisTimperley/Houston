import os
import logging
from typing import Dict, Any, Type, List

import yaml

from .connection import CommandLong
from ..valueRange import ContinuousValueRange, DiscreteValueRange
from ..command import Parameter, Command, CommandMeta
from ..specification import Idle

logger = logging.getLogger(__name__)  # type: logging.Logger
logger.setLevel(logging.DEBUG)


def create_command(command: Dict[str, Any]) -> Type[Command]:
    """
    From a given dictionary, generates the Command class.
    """
    try:
        name = command['name']
    except KeyError:
        msg = "missing 'name' field of Command"
        raise TypeError(msg)
    try:
        id = command['id']
    except KeyError:
        msg = "missing 'id' field of Command"
        raise TypeError(msg)
    parameters = {}  # type: Dict[str, Union[int, Tuple[str, Parameter]]]
    for i in range(1, 8):
        p = 'p{}'.format(i)
        if p in command:
            param = None
            try:
                p_name = command[p]['name']
            except KeyError:
                msg = "missing 'name' field of Command parameter {}".format(p)
                raise TypeError(msg)
            try:
                typ = command[p]['value']['type']
            except KeyError:
                msg = "missing 'value' or 'type' field of Command parameter {}"
                msg = msg.format(p)
                raise TypeError(msg)
            if typ == 'discrete':
                vals = command[p]['value']['vals']
                param = Parameter(p_name, DiscreteValueRange(vals))
            elif typ == 'continuous':
                min_value = command[p]['value']['min']
                max_value = command[p]['value']['max']
                param = Parameter(p_name, ContinuousValueRange(min_value,
                                                               max_value,
                                                               True))
            else:
                msg = "The type of value {} is not supported".format(typ)
                raise Exception(msg)
            parameters['param_{}'.format(i)] = param
        else:
            parameters['param_{}'.format(i)] = 0

    def to_message(self):
        params = {}
        for name, p in parameters.items():
            if not p:
                params[name] = p
            else:
                params[name] = self[p.name]
        return CommandLong(0, 0, id, **params)

    ns = {'name': name,
          'to_message': to_message,
          'parameters': [p for p in parameters.values() if p],
          'specifications': [Idle]}

    C = CommandMeta(name, (Command,), ns)

    logger.info("Command class generated: %s", C)
    return C


def read_commands_yml(filename: str) -> List[Type[Command]]:
    """
    Reads a yaml file provided by filename and creates
    Command classes and returns a list of those classes.
    """
    all_commands = []
    with open(filename, 'r') as f:
        all_commands = yaml.load(f)['commands']
    classes = [create_command(c) for c in all_commands]
    return classes
