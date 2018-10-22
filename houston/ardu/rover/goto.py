__all__ = ['GoTo']

import dronekit
import geopy.distance

from ..connection import CommandLong
from ...configuration import Configuration
from ...state import State
from ...environment import Environment
from ...command import Command, Parameter
from ...specification import Idle, Specification
from ...valueRange import ContinuousValueRange, DiscreteValueRange
from ..common import GotoLoiter


def timeout(a, s, e, c) -> float:
    from_loc = (s.latitude, s.longitude)
    to_loc = (a['latitude'], a['longitude'])
    dist = geopy.distance.great_circle(from_loc, to_loc).meters
    timeout = dist * c.time_per_metre_travelled
    timeout += c.constant_timeout_offset
    return timeout


GotoNormally = Specification(
    'normal',
    '(and (= _armed true) (not (= _mode "LOITER")))',
    '(and (= __longitude $longitude) (= __latitude $latitude))',
    timeout)


class GoTo(Command):
    uid = 'ardu:rover:goto'
    name = 'goto'
    parameters = [
        Parameter('latitude', ContinuousValueRange(-90.0, 90.0, True)),
        Parameter('longitude', ContinuousValueRange(-180.0, 180.0, True))
    ]
    specifications = [
        GotoNormally,
        GotoLoiter,
        Idle
    ]

    def dispatch(self,
                 sandbox: 'Sandbox',
                 state: State,
                 environment: Environment,
                 config: Configuration
                 ) -> None:
        loc = dronekit.LocationGlobalRelative(self.latitude,
                                              self.longitude,
                                              state.altitude)
        sandbox.connection.simple_goto(loc)

    def to_message(self) -> CommandLong:
        return CommandLong(0,
                           0,
                           cmd_id=mavutil.MAV_CMD_NAV_WAYPOINT,
                           param1=2,  # FIXME frame?
                           param5=self.latitude,
                           param6=self.longitude)
