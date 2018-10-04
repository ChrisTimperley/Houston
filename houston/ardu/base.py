__all__ = ['BaseSystem']

from typing import List, Type

from ..system import System
from ..command import Command


class BaseSystem(System):
    is_abstract = True

    def __init__(self,
                 commands: List[Type[Command]],
                 ) -> None:
        super().__init__(commands)
