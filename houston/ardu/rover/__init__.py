__all__ = ['ArduRover']

from bugzoo.client import Client as BugZooClient

from .sandbox import Sandbox
from .state import State
from ..base import BaseSystem
from ..configuration import Configuration
from .goto import GoTo


class ArduRover(BaseSystem):
    name = 'ardurover'
    state = State
    sandbox = Sandbox
    schemas = []

    def __init__(self,
                 configuration: Configuration
                 ) -> None:
        from ..common import ArmDisarm
        from .goto import GoTo

        # TODO: RTL_ALT: http://ardupilot.org/copter/docs/rtl-mode.html
        # rover-specific system variables
        commands = [
            GoTo,
            ArmDisarm
        ]
        super().__init__(commands, configuration)
