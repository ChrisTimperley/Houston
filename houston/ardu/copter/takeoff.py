__all__ = ['Takeoff']

import time
import math

from pymavlink import mavutil

from ..connection import CommandLong
from ...configuration import Configuration
from ...state import State
from ...specification import Specification
from ...environment import Environment
from ...command import Parameter, Command
from ...specification import Specification, Idle
from ...valueRange import ContinuousValueRange


def timeout(a, s, e, c) -> float:
    # FIXME add rate of ascent
    delta_alt = abs(a['altitude'] - s.altitude)
    t = delta_alt * c.time_per_metre_travelled
    t += c.constant_timeout_offset
    return t


TakeoffNormally = Specification(
    'normal',
    """
    (and
        (= _armed true)
        (= _mode "GUIDED")
        (< _altitude 0.3))
    """,
    """
    (and
        (= _longitude __longitude)
        (= _latitude __latitude)
        (= __altitude $altitude)
        (= __vz 0.0))
    """,
    timeout)


class Takeoff(Command):
    uid = 'ardu:copter:takeoff'
    name = 'takeoff'
    parameters = [
        Parameter('altitude', ContinuousValueRange(0.3, 100.0))
    ]
    specifications = [
        TakeoffNormally,
        Idle
    ]

    def dispatch(self,
                 sandbox: 'Sandbox',
                 state: State,
                 environment: Environment,
                 config: Configuration
                 ) -> None:
        vehicle = sandbox.connection
        msg = vehicle.message_factory.command_long_encode(
            0, 0,
            mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
            0, 1, 0, 0, 0, 0, 0, self.altitude)
        vehicle.send_mavlink(msg)

    def to_message(self) -> CommandLong:
        msg = CommandLong(
            target_system=0,
            target_component=0,
            cmd_id=mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
            param_1=0,
            param_7=self.altitude)
        return msg
