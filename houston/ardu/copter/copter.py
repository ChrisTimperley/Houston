__all__ = ['ArduCopter']

import logging
import os

from .state import State
from .sandbox import Sandbox
from .goto import GoTo
from .setmode import SetMode
from .takeoff import Takeoff
from .parachute import Parachute
from ..command_factory import read_commands_yml
from ..base import BaseSystem
from ..common import ArmDisarm
from ..configuration import Configuration

logger = logging.getLogger(__name__)  # type: logging.Logger
logger.setLevel(logging.DEBUG)

dirname = os.path.dirname(__file__)


class ArduCopter(BaseSystem):
    name = 'arducopter'
    state = State
    sandbox = Sandbox
    configuration = Configuration
#    commands = [
#        GoTo,
#        Takeoff,
#        ArmDisarm,
#        SetMode,
#        Parachute
#        ]
    commands = read_commands_yml(os.path.join(dirname, 'commands.yml'))
