__all__ = ['ArduRover']

from .sandbox import Sandbox
from .state import State
from .goto import GoTo
from ..base import BaseSystem
from ..common import ArmDisarm


class ArduRover(BaseSystem):
    name = 'ardurover'
    state = State
    sandbox = Sandbox
    commands = [
        GoTo,
        ArmDisarm
    ]
