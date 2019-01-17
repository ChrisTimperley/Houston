import houston
from houston.environment import Environment
from houston.ardu.copter.state import State as CopterState
from houston.ardu.rover.state import State as RoverState
from houston.ardu.configuration import Configuration as ArduConfig

from houston.ardu.copter import Takeoff, GoTo, ArmDisarm, SetMode


snapshot = 'ardubugs:742cdf6b'

def build_config(speedup: int):
    assert speedup >= 1
    return ArduConfig(speedup=speedup,
                      time_per_metre_travelled=5.0,
                      constant_timeout_offset=1.0,
                      min_parachute_alt=10.0)

sut = houston.ardu.copter.copter.ArduCopter

# mission description
cmds = (
    ArmDisarm(arm=False),
    ArmDisarm(arm=True),
    #SetMode(mode='GUIDED'),
    #Takeoff(altitude=3.0),
    #GoTo(latitude=-35.361354, longitude=149.165218, altitude=5.0),
    #SetMode(mode='LAND'),
    #ArmDisarm(arm=False)
)

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

