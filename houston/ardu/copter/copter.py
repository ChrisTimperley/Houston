__all__ = ['ArduCopter']

import logging

from .state import State
from .sandbox import Sandbox
from ..base import BaseSystem

logger = logging.getLogger(__name__)  # type: logging.Logger
logger.setLevel(logging.DEBUG)


class ArduCopter(BaseSystem):
    name = 'arducopter'
    state = State
    sandbox = Sandbox
    schemas = []

    def __init__(self) -> None:
        from common import ArmDisarm
        from houston.ardu.copter.goto import GoTo
        from houston.ardu.copter.setmode import SetMode
        from houston.ardu.copter.takeoff import Takeoff
        from houston.ardu.copter.parachute import Parachute
        commands = [
            GoTo,
            Takeoff,
            ArmDisarm,
            SetMode,
            Parachute
        ]
        super().__init__(commands)
