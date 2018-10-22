from typing import Set, Optional, Tuple, Dict, List, Any,\
    Type
import random

from ..system import System
from ..state import State
from ..environment import Environment
from ..mission import Mission, MissionOutcome
from ..valueRange import DiscreteValueRange
from ..command import Command, Parameter
from ..configuration import Configuration

Domain = List[Tuple[int, Type[Command], List[Parameter]]]


class MissionDomain(object):
    """
    Specification of a range of missions.
    """
    def __init__(self,
                 system: Type[System],
                 initial_domain: Domain = None
                 ) -> None:
        if not initial_domain:
            initial_domain = []
        self.__domain = initial_domain
        self.__system = system

    def __str__(self) -> str:
        return str(self.domain)

    @property
    def domain(self) -> Domain:
        """
        The domain specified by sequence of Actions with
        specific parameter ranges.
        """
        return self.__domain

    @property
    def system(self) -> Type[System]:
        """
        Returns the system that this mission domain belongs to.
        """
        return self.__system

    @staticmethod
    def from_initial_mission(mission: Mission,
                             discrete_params: bool = False)\
            -> 'MissionDomain':
        """
        Create a mission domain by considering the initial sequence
        of actions in mission and all possible values for parameters.
        """
        i = 0
        domain = []
        for command in mission.commands:
            if discrete_params:
                parameters = [Parameter(p.name,
                                        DiscreteValueRange([command[p.name]]))
                              for p in command.parameters]
            else:
                parameters = command.parameters
            domain.append((i, command.__class__, parameters))
            i += 1
        return MissionDomain(mission.system, domain)

    @property
    def command_size(self) -> int:
        """
        Number of actions in this domain.
        """
        return len(self.__domain)

    def generate_mission(self,
                         environment: Environment,
                         initial_state: State,
                         config: Configuration,
                         rng: random.Random
                         ) -> Mission:
        """
        Return a mission in this domain.
        """
        cmds = []
        for _, cmd_class, params in self.domain:
            parameters = {}
            for p in params:
                parameters[p.name] = p.generate(rng)
            cmds.append(cmd_class(**parameters))
        return Mission(config, environment, initial_state, cmds, self.system)


class RootCauseFinder(object):
    """
    RootCauseFinder is used to find minimum requirements that
    results in mission failure the same way that initial failing
    missions do.
    """
    def __init__(self,
                 system: Type[System],
                 initial_state: State,
                 environment: Environment,
                 config: Configuration,
                 initial_failing_missions: List[Mission],
                 random_seed: int = 100
                 ) -> None:

        assert(len(initial_failing_missions) > 0)

        self.__system = system
        self.__initial_state = initial_state
        self.__environment = environment
        self.__rng = random.Random(random_seed)
        self.__initial_failing_missions = initial_failing_missions
        self.__configuration = config

    @property
    def system(self) -> Type[System]:
        """
        The system under test.
        """
        return self.__system

    @property
    def initial_state(self) -> State:
        """
        the initial state used for running all missions.
        """
        return self.__initial_state

    @property
    def environment(self) -> Environment:
        """
        the environment used for running all missions.
        """
        return self.__environment

    @property
    def initial_failing_missions(self) -> Mission:
        """
        the failing missions provided by the user.
        """
        return self.__initial_failing_missions

    @property
    def configuration(self) -> Configuration:
        return self.__configuration

    @property
    def rng(self) -> random.Random:
        return self.__rng

    def find_root_cause(self, time_limit: float = 0.0) -> MissionDomain:
        """
        The main function that finds the root cause.
        """
        raise NotImplementedError
