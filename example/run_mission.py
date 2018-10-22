import logging

import houston
import bugzoo
from houston import Environment, Mission
from houston.ardu.configuration import Configuration
from houston.ardu.copter import ArmDisarm, Takeoff, SetMode, GoTo
from houston.ardu.copter.state import State
from houston.ardu.copter.sandbox import Sandbox
from houston.ardu.copter.copter import ArduCopter


def main():
    # setup logging
    log_to_stdout = logging.StreamHandler()
    log_to_stdout.setLevel(logging.DEBUG)
    logging.getLogger('houston').addHandler(log_to_stdout)

    bz = bugzoo.BugZoo()

    # construct a test
    environment = Environment({})
    configuration = ArduCopter.configuration(
        speedup=1,
        time_per_metre_travelled=5.0,
        constant_timeout_offset=1.0,
        min_parachute_alt=10.0)
    commands = [
#        ArmDisarm(arm=True),
#        ArmDisarm(arm=False),
        Takeoff(altitude=3.0),
        GoTo(latitude=-35.3632607, longitude=149.1662351, altitude=3.4)
#        SetMode(mode='LAND'),
#        ArmDisarm(arm=False)
    ]
    state_initial = ArduCopter.state(
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
    mission = Mission(configuration,
                      environment,
                      state_initial,
                      commands,
                      ArduCopter)

    # the Docker image that provides the SUT
    snapshot = 'ardubugs:742cdf6b'
    #with Sandbox.for_snapshot(bz, snapshot, state_initial, environment, configuration) as sandbox:  # noqa: pycodestyle
    #    outcome = sandbox.run(commands)
    outcome = mission.run(bz, snapshot)

    print(outcome)


if __name__ == '__main__':
    main()
