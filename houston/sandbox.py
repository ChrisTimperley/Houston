from typing import Set, Optional, Tuple, Dict, Sequence, Iterator
from timeit import default_timer as timer
from contextlib import contextmanager
import math
import time
import threading
import signal
import logging

import bugzoo
from bugzoo.client import Client as BugZooClient
from bugzoo.core.container import Container
from bugzoo.core.fileline import FileLineSet

from .state import State
from .mission import MissionOutcome
from .command import Command, CommandOutcome

logger = logging.getLogger(__name__)  # type: logging.Logger
logger.setLevel(logging.DEBUG)


class Sandbox(object):
    """
    Sandboxes are used to provide an isolated, idempotent environment for
    executing test cases on a given system.
    """
    @staticmethod
    @contextmanager
    def launch(client_bugzoo: BugZooClient,
               container: Container,
               state_initial: State,
               environment: Environment,
               configuration: Configuration
               ) -> Iterator['Sandbox']:
        """
        Launches an interactive sandbox instance within a given Docker
        container. The sandbox instance within the container is automatically
        started and stopped upon entering and leaving its context.
        """
        sandbox = Sandbox(client_bugzoo,
                          container,
                          state_initial,
                          environment,
                          configuration)
        try:
            sandbox.start()
            yield sandbox
        finally:
            sandbox.stop()

    def __init__(self,
                 client_bugzoo: BugZooClient,
                 container: Container,
                 state_initial: State,
                 environment: Environment,
                 configuration: Configuration
                 ) -> None:
        self.__lock = threading.Lock()
        self._bugzoo = client_bugzoo
        self.__container = container
        self.__state = state_initial
        self.__environment = environment
        self.__configuration = configuration

    @property
    def running_time(self) -> float:
        """
        Returns the number of seconds (wall-clock time) that have elapsed
        since this sandbox session begun.
        """
        raise NotImplementedError

    @property
    def state(self) -> State:
        """
        The last observed state of the system under test.
        """
        return self.__state

    @property
    def configuration(self) -> Configuration:
        """
        The configuration used by the system under test.
        """
        return self.__configuration

    @property
    def environment(self) -> Environment:
        """
        A description of the simulated environment.
        """
        return self.__environment

    @property
    def container(self) -> Container:
        """
        The BugZoo container underlying this sandbox.
        """
        return self.__container

    def start(self) -> None:
        """
        Starts the SITL instance for this sandbox.
        """
        raise NotImplementedError

    def stop(self) -> None:
        """
        Stops the SITL instance for this sandbox.
        """
        raise NotImplementedError

    def issue(self, command: Command) -> None:
        """
        Non-blocking for now.
        """
        # FIXME send message via connection
        command.dispatch(self,
                         self.state,
                         self.configuration,
                         self.environment)

    def run_command(self,
                    command: Command,
                    *,
                    timeout: Optional[float] = None
                    ) -> CommandOutcome:
        logger.debug('running command: %s', command)

        env = self.environment
        config = self.configuration
        time_start = self.running_time
        state_after = state_before = self.state

        # determine which spec the system should observe
        spec = cmd.resolve(state_before, env, config)
        postcondition = spec.postcondition
        def is_sat() -> bool:
            return postcondition.is_satisfied(command,
                                              state_before,
                                              state_after,
                                              env,
                                              config)
        logger.debug('enforcing specification: %s', spec)

        # determine timeout using specification is no timeout
        # is provided
        if timeout is None:
            timeout = cmd.timeout(state_before, env, config)
        logger.debug("enforcing timeout: %.3f seconds", timeout)

        self.issue(command)

        # FIXME block until completion message or timeout occurs
        time_elapsed = 0.0
        time_start = timer()
        while not is_sat() and time_elapsed < timeout:
            self.observe()
            state_after = self.state
            time.sleep(0.1)
            time_elapsed = timer() - time_start

        passed = is_sat()
        outcome = CommandOutcome(command,
                                 passed,
                                 state_before,
                                 state_after,
                                 time_elapsed)
        return outcome


    def run(self, commands: Sequence[Command]) -> MissionOutcome:
        """
        Executes a mission, represented as a sequence of commands, and
        returns a description of the outcome.
        """
        config = self.configuration
        env = self.environment
        time_start = timer()
        time_elapsed = 0.0
        with self.__lock:
            outcomes = []  # type: List[CommandOutcome]
            for cmd in mission:
                outcome = self.run_command()
                outcomes.append(outcome)
                if not outcome.successful:
                    break
            time_elapsed = timer() - time_start
            return MissionOutcome(passed, outcomes, time_elapsed)

    def observe(self) -> None:
        """
        Triggers an observation of the current state of the system under test.
        """
        state_class = self.state.__class__
        variables = state_class.variables
        values = {v.name: v.read(self) for v in variables}
        values['time_offset'] = self.running_time
        state_new = state_class.from_json(values)  # FIXME this is a hack
        self.__state = state_new
