#!/usr/bin/env python3
import copy
import json
import logging

import bugzoo
from bugzoo import BugZoo

import houston
from houston.command import Command
from houston.environment import Environment
from houston.generator.rand import RandomMissionGenerator
from houston.generator.resources import ResourceLimits
from houston.mission import Mission
from houston.runner import MissionRunnerPool
#from houston.ardu.common.goto import CircleBasedGotoGenerator
from houston.root_cause.delta_debugging import DeltaDebugging
from houston.root_cause.symex import SymbolicExecution
import copy
from houston.ardu.copter.state import State as CopterState
from houston.ardu.rover.state import State as RoverState
from houston.ardu.configuration import Configuration as ArduConfig


from houston.ardu.copter import Takeoff, GoTo, ArmDisarm, SetMode


def setup_logging() -> None:
    log_to_stdout = logging.StreamHandler()
    log_to_stdout.setLevel(logging.DEBUG)
    logging.getLogger('houston').addHandler(log_to_stdout)


def run_single_mission(sandbox, mission):
    res = sandbox.run(mission)
    print(res)

def run_single_mission_with_coverage(sandbox, mission):
    (res, coverage) = sandbox.run_with_coverage(mission)
    print("Done")
    print(coverage)

### Run all missions stored to a json file
def run_all_missions(sut, mission_file, coverage=False):
    missions = []
    with open(mission_file, "r") as f:
        missions_json = json.load(f)
        missions = list(map(Mission.from_json, missions_json))
    assert isinstance(missions, list)


    outcomes = {}
    coverages = {}
    def record_outcome(mission, outcome, coverage=None):
        outcomes[mission] = outcome
        coverages[mission] = coverage

    runner_pool = MissionRunnerPool(sut, 4, missions, record_outcome, coverage)
    print("Started running")
    runner_pool.run()
    print("Done running")
    print(outcomes)

    with open("example/failed.json", "w") as f:
        for m in outcomes:
            if not outcomes[m].passed:
                f.write(str(m.to_json()))
                f.write("\n")

    if coverage:
        from bugzoo.core.coverage import TestSuiteCoverage
        from bugzoo.core.spectra import Spectra
        from bugzoo.localization import Localization
        from bugzoo.localization.suspiciousness import tarantula
        test_suite_coverage_dict = {}
        counter = 0
        for m in coverages:
            test = {
                    'test': 't{}'.format(counter),
                    'outcome': outcomes[m].to_test_outcome_json(0),
                    'coverage': coverages[m].to_dict()
            }
            test_suite_coverage_dict['t{}'.format(counter)] = test
            counter += 1
        spectra = Spectra.from_coverage(TestSuiteCoverage.from_dict(test_suite_coverage_dict))
        l = Localization.from_spectra(spectra, tarantula)
        print(str(l.get_most_suspicious_lines()))
        with open("example/localization.json", "w") as f:
            f.write(str(l))

### Generate missions
def generate(sut, initial, environment, number_of_missions, max_num_actions=3):
    mission_generator = RandomMissionGenerator(sut, initial, environment, max_num_actions=max_num_actions, action_generators=[CircleBasedGotoGenerator((-35.3632607, 149.1652351), 2.0)])
    resource_limits = ResourceLimits(number_of_missions, 1000)
    missions = mission_generator.generate(100, resource_limits)
    print("### {}".format(missions))
    with open("example/missions.json", "w") as f:
        mission_descriptions = list(map(Mission.to_json, missions))
        print(str(mission_descriptions))
        json.dump(mission_descriptions, f)


### Generate and run missions
def generate_and_run(sut, initial, environment, number_of_missions):
    mission_generator = RandomMissionGenerator(sut, initial, environment)
    resource_limits = ResourceLimits(number_of_missions, 1000)
    mission_generator.generate_and_run(100, resource_limits)
    #mission_generator.prepare(100, resource_limits)
    #for i in range(number_of_missions):
    #    m = mission_generator.generate_mission()
    #    print("Mission {}: {}".format(i, m.to_json()))
    #    res = sandbox.run(m)
    print("DONE")


### Generate and run missions with mutation operator
def generate_and_run_mutation(sut, initial_state, environment, initial_mission, number_of_missions):
    mission_generator = MutationBasedMissionGenerator(sut, initial, environment, initial_mission, action_generators=[CircleBasedGotoGenerator((-35.3632607, 149.1652351), 2.0)])
    resource_limits = ResourceLimits(number_of_missions*5, 1000, number_of_missions)
    mission_generator.generate_and_run(100, resource_limits, with_coverage=True)
    print("DONE")
    with open("example/missions-mutation.json", "w") as f:
        mission_descriptions = list(map(Mission.to_json, mission_generator.history))
        print(str(mission_descriptions))
        json.dump(mission_descriptions, f)
        f.write("\n")
        mission_descriptions = list(map(Mission.to_json, mission_generator.most_fit_missions))
        print(str(mission_descriptions))
        json.dump(mission_descriptions, f)



### Generate and run missions with fault localization
def generate_and_run_with_fl(sut, initial, environment, number_of_missions):
    mission_generator = RandomMissionGenerator(sut, initial, environment, max_num_actions=3, action_generators=[CircleBasedGotoGenerator((-35.3632607, 149.1652351), 2.0)])
    resource_limits = ResourceLimits(number_of_missions, 1000)
    report = mission_generator.generate_and_run(100, resource_limits, with_coverage=True)
    print("DONE")
    print(report)
    print(mission_generator.coverage)
    print(mission_generator.report_fault_localization())
    with open("fl.json", "w") as f:
        f.write(str(mission_generator.report_fault_localization()))


### Generate missions with symbolic execution
def generate_with_se(sut, initial, environment, config, mission):
    se = SymbolicExecution(sut, initial, environment, config)
    missions = se.execute_symbolically(mission)
    with open("example/missions.json", "w") as f:
        mission_descriptions = list(map(Mission.to_dict, missions))
        print(str(mission_descriptions))
        json.dump(mission_descriptions, f)


if __name__ == "__main__":
    setup_logging()
    bz = BugZoo()
    snapshot = bz.bugs['ardubugs:742cdf6b']
    #snapshot = bz.bugs['afrl:AIS-Scenario1']

    config = ArduConfig(
        speedup=1,
        time_per_metre_travelled=5.0,
        constant_timeout_offset=1.0,
        min_parachute_alt=10.0)
    sut = houston.ardu.ArduCopter(snapshot, config)

    # mission description
    cmds = [
        ArmDisarm(arm=False),
        ArmDisarm(arm=True),
        #SetMode(mode='GUIDED'),
        Takeoff(altitude=3.0),
        #GoTo(latitude=-35.361354, longitude=149.165218, altitude=5.0),
        SetMode(mode='LAND'),
        ArmDisarm(arm=False)
    ]

    environment = Environment({})
    initial = CopterState(
        home_latitude=-35.3632607,
        home_longitude=149.1652351,
        latitude=-35.3632607,
        longitude=149.1652351,
        altitude=0.0,
        armed=False,
        armable=True,
        mode="GUIDED",
        ekf_ok=True,
        yaw=0.0,
        roll=0.0,
        pitch=0.0,
        roll_channel=0.0,
        throttle_channel=0.0,
        heading=0.0,
        groundspeed=0.0,
        airspeed=0.0,
        vx=0.0,
        vy=0.0,
        vz=0.0,
        time_offset=0.0)
    mission = Mission(config, environment, initial, cmds)

    # create a container for the mission execution
    sandbox = sut.provision(bz)
    try:
        run_single_mission(sandbox, mission)
        #run_single_mission_with_coverage(sandbox, mission)
        #generate(sut, initial, environment, 100, 10)
        #run_all_missions(sut, "example/missions.json", False)
        #generate_and_run_mutation(sut, initial, environment, mission, 3)
        #generate_and_run_with_fl(sut, initial, environment, 5)
        #run_single_mission_with_coverage(sandbox, mission)

        #d = DeltaDebugging(sut, initial, environment, config, [mission])
        #d.find_root_cause()


        #generate(sut, initial, environment, 100, 10)
        # run_all_missions(sut, "example/missions.json", False)
        #generate_and_run_with_fl(sut, initial, environment, 5)
        #run_single_mission_with_coverage(sandbox, mission)

        #generate_with_se(sut, initial, environment, config, mission)

    finally:
        #pass
        sandbox.destroy()
