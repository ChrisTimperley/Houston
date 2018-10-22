from typing import Set, Optional, Tuple, Dict, List, Type
from bugzoo.client import Client as BugZooClient

from .root_cause import RootCauseFinder, MissionDomain
from ..system import System
from ..state import State
from ..environment import Environment
from ..mission import Mission
from ..configuration import Configuration


class DeltaDebugging(RootCauseFinder):
    """
    Conducts delta debugging on a failing mission to narrow
    it down to main problem.
    """
    def __init__(self,
                 system: Type[System],
                 initial_state: State,
                 environment: Environment,
                 config: Configuration,
                 initial_failing_missions: List[Mission],
                 bz: BugZooClient,
                 snapshot: str
                 ) -> None:
        self.__domain = MissionDomain.from_initial_mission(
            initial_failing_missions[0], discrete_params=True)
        self.__bz = bz
        self.__snapshot = snapshot

        super(DeltaDebugging, self).__init__(system, initial_state,
                                             environment, config,
                                             initial_failing_missions)

    @property
    def domain(self) -> MissionDomain:
        """
        The domain where the failure happens.
        """
        return self.__domain

    def find_root_cause(self, time_limit: float = 0.0) -> MissionDomain:
        empty_domain = MissionDomain(self.system)
        final_domain = self._dd2(self.domain, empty_domain)
        print("FINISHED: {}".format(str(final_domain)))

        return final_domain

    def _dd2(self, c: MissionDomain, r: MissionDomain) -> MissionDomain:

        print("****** C: {}\n****** R: {}".format(str(c), str(r)))

        if c.command_size == 1:
            return c

        c1, c2 = DeltaDebugging._divide(c)

        m1 = DeltaDebugging._union(c1, r)
        res = self._run(m1)
        if not res:
            return self._dd2(c1, r)

        m2 = DeltaDebugging._union(c2, r)
        res = self._run(m2)
        if not res:
            return self._dd2(c2, r)

        final_domain = DeltaDebugging._union(self._dd2(c1, m2),
                                             self._dd2(c2, m1))
        return final_domain

    def _run(self, mission_domain: MissionDomain) -> bool:
        """
        runs a mission using sandbox and returns whether the mission passed.
        """
        mission = mission_domain.generate_mission(self.environment,
                                                  self.initial_state,
                                                  self.configuration,
                                                  self.rng)
        res = mission.run(self.__bz, self.__snapshot)

        return res.passed

    @staticmethod
    def _divide(c: MissionDomain) -> Tuple[MissionDomain, MissionDomain]:
        """
        Divides a domain into two almost equal domains.
        """
        mid = int(c.command_size / 2)
        c1 = MissionDomain(c.system, c.domain[:mid])
        c2 = MissionDomain(c.system, c.domain[mid:])
        return c1, c2

    @staticmethod
    def _union(c1: MissionDomain, c2: MissionDomain) -> MissionDomain:
        """
        Returns the union of two domains.
        """
        command_list = []
        i1, i2 = 0, 0
        while i1 < c1.command_size or i2 < c2.command_size:
            if i1 >= c1.command_size or \
               (i2 < c2.command_size and c2.domain[i2][0] < c1.domain[i1][0]):
                command_list.append(c2.domain[i2])
                i2 += 1
            else:
                command_list.append(c1.domain[i1])
                i1 += 1
        c = MissionDomain(c1.system, command_list)
        return c
