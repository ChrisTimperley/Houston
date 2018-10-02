from .state import State

from bugzoo.client import Client as BugZooClient
from bugzoo.core.container import Container


class SITL(object):
    # FIXME use a contextmanager
    @staticmethod
    def launch(client_bugzoo: BugZooClient,
               container: Container
               ) -> SITL:
        return

    def __init__(self,
                 state_initial: State,
                 configuration: Configuration
                 ) -> None:
        self.__time = 0.0  # FIXME wall-clock or sim time?
        self.__state = state_initial
        self.__configuration = configuration

    def start(self) -> None:
        """
        Starts the execution of the SITL.
        """
        raise NotImplementedError

    def stop(self) -> None:
        """
        Stops the execution of the SITL.
        """
        raise NotImplementedError

    def execute(self, command: Command) -> None:
        pass

    @property
    def state(self) -> State:
        """
        The last observed state of the system under test.
        """
        return self.__state
