__all__ = ['ArduRover']

from .sandbox import Sandbox
from .state import State
from .goto import GoTo
from ..base import BaseSystem
from ..common import ArmDisarm
from ..configuration import Configuration


class ArduRover(BaseSystem):
    name = 'ardurover'
    state = State
    sandbox = Sandbox
    configuration = Configuration
    commands = [
        GoTo,
        ArmDisarm
    ]
