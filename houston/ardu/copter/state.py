__all__ = ['State']

from ..connection import MAVLinkMessage, MAVLinkConnection
from ...state import State as BaseState
from ...state import var

# These are the messages we should later listen to
IMPORTANT_MESSAGE_NAMES = [
    'GLOBAL_POSITION_INT',
    'ATTITUDE',
    'VFR_HUD',
    'SYS_STATUS',
    'EKF_STATUS_REPORT',
    'HEARTBEAT',
    'HOME_POSITION',
]


class State(BaseState):
    home_latitude = var(float, lambda c: -35.362938)  # TODO: fixed
    home_longitude = var(float, lambda c: 149.165085)  # TODO: fixed
    altitude = var(float,
                   lambda c: c.conn.location.global_relative_frame.alt,  # noqa: pycodestyle
                   noise=0.01)
    latitude = var(float,
                   lambda c: c.conn.location.global_relative_frame.lat,  # noqa: pycodestyle
                   noise=0.0005)
    longitude = var(float,
                    lambda c: c.conn.location.global_relative_frame.lon,  # noqa: pycodestyle
                    noise=0.0005)
    armable = var(bool, lambda c: c.conn.is_armable)
    armed = var(bool, lambda c: c.conn.armed)
    mode = var(str, lambda c: c.conn.mode.name)
    vx = var(float, lambda c: c.conn.velocity[0], noise=0.05)
    vy = var(float, lambda c: c.conn.velocity[1], noise=0.05)
    vz = var(float, lambda c: c.conn.velocity[2], noise=0.05)
    pitch = var(float, lambda c: c.conn.attitude.pitch, noise=0.05)
    yaw = var(float, lambda c: c.conn.attitude.yaw, noise=0.05)
    roll = var(float, lambda c: c.conn.attitude.roll, noise=0.05)
    heading = var(float, lambda c: c.conn.heading, noise=2)
    airspeed = var(float, lambda c: c.conn.airspeed, noise=0.05)
    groundspeed = var(float, lambda c: c.conn.groundspeed, noise=0.05)
    ekf_ok = var(bool, lambda c: c.conn.ekf_ok)
    throttle_channel = var(float, lambda c: c.conn.channels['3'])
    roll_channel = var(float, lambda c: c.conn.channels['1'])

    def evolve(self,
               message: MAVLinkMessage,
               time_offset: float,
               connection: MAVLinkConnection
               ) -> 'State':
        values = {name: v.read(connection)
                  for (name, v) in self.variables.items()}
        values['time_offset'] = time_offset
        state_new = self.__class__(**values)
        return state_new
