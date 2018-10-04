__all__ = ['ArduCopter']

import logging

from .state import State
from .sandbox import Sandbox
from .goto import GoTo
from .setmode import SetMode
from .takeoff import Takeoff
from .parachute import Parachute
from ..base import BaseSystem
from ..common import ArmDisarm

logger = logging.getLogger(__name__)  # type: logging.Logger
logger.setLevel(logging.DEBUG)


class ArduCopter(BaseSystem):
    name = 'arducopter'
    state = State
    sandbox = Sandbox
    commands = [
        GoTo,
        Takeoff,
        ArmDisarm,
        SetMode,
        Parachute
    ]
