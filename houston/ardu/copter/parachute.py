__all__ = ['Parachute']

from pymavlink import mavutil

from ..connection import CommandLong
from ...connection import Message
from ...configuration import Configuration
from ...state import State
from ...specification import Specification
from ...environment import Environment
from ...command import Parameter, Command
from ...specification import Specification, Idle
from ...valueRange import DiscreteValueRange


def timeout_parachute_normally(a, s, e, c) -> float:
    timeout = s.altitude * c.time_per_metre_travelled
    timeout += c.constant_timeout_offset
    return timeout


ParachuteNormally = Specification(
    'normal',
    """
    (and
        (= $parachute_action 2)
        (= _armed true)
        (= _mode "GUIDED")
        (> _altitude 10.0))
    """,
    """
    (and
        (= __armed false)
        (< __altitude 0.3)
        (= __vz 0.0))
    """,
    timeout_parachute_normally)


class Parachute(Command):
    uid = 'ardu:copter:parachute'
    name = 'parachute'
    parameters = [
        # 0=disable, 1=enable, 2=release
        Parameter('parachute_action', DiscreteValueRange([0, 1, 2]))
    ]
    specifications = [
        ParachuteNormally,
        Idle
    ]

    def to_message(self) -> Message:
        return CommandLong(cmd_id=208,
                           param1=self.parachute_action)

    def dispatch(self,
                 sandbox: 'Sandbox',
                 state: State,
                 environment: Environment,
                 config: Configuration
                 ) -> None:
        vehicle = sandbox.connection
        msg = vehicle.message_factory.command_long_encode(
            0, 0,
            mavutil.mavlink.MAV_CMD_DO_PARACHUTE,
            0, self.parachute_action, 0, 0, 0, 0, 0, 0)
        vehicle.send_mavlink(msg)
