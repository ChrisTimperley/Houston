__all__ = ['ArduRover']

from bugzoo.client import Client as BugZooClient
from bugzoo.core.bug import Bug as Snapshot

from .sandbox import Sandbox
from .state import State
from ..base import BaseSystem
from ..configuration import Configuration


class ArduRover(BaseSystem):
    state = State
    schemas = []

    def __init__(self,
                 snapshot: Snapshot,
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
        super().__init__(snapshot, commands, configuration)

    def provision(self, client_bugzoo: BugZooClient) -> Sandbox:
        return Sandbox(self, client_bugzoo)
