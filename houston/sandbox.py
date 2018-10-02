from typing import Set, Optional, Tuple, Dict, Sequence
from timeit import default_timer as timer
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
from .util import TimeoutError, printflush
from .command import Command, CommandOutcome

logger = logging.getLogger(__name__)  # type: logging.Logger
logger.setLevel(logging.DEBUG)


class Sandbox(object):
    """
    Sandboxes are used to provide an isolated, idempotent environment for
    executing test cases on a given system.
    """
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

    def _start(self) -> None:
        """
        Starts the SITL instance for this sandbox.
        """
        raise NotImplementedError

    def _stop(self) -> None:
        """
        Stops the SITL instance for this sandbox.
        """
        raise NotImplementedError

    def run(self, commands: Sequence[Command]) -> MissionOutcome:
        """
        Executes a mission, represented as a sequence of commands, and
        returns a description of the outcome.
        """
        config = self.configuration
        with self.__lock:
            time_before_setup = timer()
            logger.debug("preparing for mission")
            self._start(mission)
            setup_time = timer() - time_before_setup
            logger.debug("prepared for mission (took %.3f seconds)",
                         setup_time)

            env = mission.environment
            outcomes = []

            for cmd in mission:
                logger.debug('performing command: %s', cmd)

                # compute expected state
                start_time = time.time()
                state_before = state_after = self.observe(0.0)

                # determine which spec the system should observe
                spec = cmd.resolve(state_before, env, config)
                logger.debug('enforcing specification: %s', spec)

                # enforce a timeout
                timeout = cmd.timeout(state_before, env, config)
                logger.debug("enforcing timeout: %.3f seconds", timeout)
                time_before = timer()
                passed = False
                try:
                    # TODO: dispatch to this container!
                    cmd.dispatch(self, state_before, config, env)

                    # block until the postcondition is satisfied or
                    # the timeout is hit
                    while not passed:
                        state_after = self.observe(time.time() - start_time)
                        # TODO implement idle! (add timeout in idle dispatch)
                        sat = spec.postcondition.is_satisfied(cmd,
                                                              state_before,
                                                              state_after,
                                                              env,
                                                              config)
                        if sat:
                            logger.debug("command was successful")
                            passed = True
                            break
                        if timer() - time_before >= int(math.ceil(timeout)):
                            raise TimeoutError
                        time.sleep(0.1)
                        logger.debug("state: %s", state_after)

                except TimeoutError:
                    logger.debug("reached timeout before postcondition was satisfied")  # noqa: pycodestyle
                time_elapsed = timer() - time_before

                # record the outcome of the command execution
                outcome = CommandOutcome(cmd,
                                         passed,
                                         state_before,
                                         state_after,
                                         time_elapsed)
                outcomes.append(outcome)

                if not passed:
                    total_time = timer() - time_before_setup
                    return MissionOutcome(False,
                                          outcomes,
                                          setup_time,
                                          total_time)

            total_time = timer() - time_before_setup
            return MissionOutcome(True, outcomes, setup_time, total_time)

    def observe(self, running_time: float) -> None:
        """
        Returns an observation of the current state of the system running
        inside this sandbox.
        """
        state_class = self.state.__class__
        variables = state_class.variables
        values = {v.name: v.read(self) for v in variables}
        values['time_offset'] = running_time
        return state_class.from_json(values)
