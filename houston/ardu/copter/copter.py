__all__ = ['ArduCopter']

import logging

from bugzoo.client import Client as BugZooClient
from bugzoo.core.bug import Bug as Snapshot

from .state import State
from .sandbox import Sandbox
from ..base import BaseSystem
from ..configuration import Configuration

logger = logging.getLogger(__name__)  # type: logging.Logger
logger.setLevel(logging.DEBUG)


class ArduCopter(BaseSystem):
    name = 'arducopter'
    state = State
    schemas = []

    def __init__(self,
                 snapshot: Snapshot,
                 configuration: Configuration
                 ) -> None:
        from houston.ardu.common import ArmDisarm
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
        super().__init__(snapshot, commands, configuration)

    def provision(self, client_bugzoo: BugZooClient) -> Sandbox:
        return Sandbox(self, client_bugzoo)
