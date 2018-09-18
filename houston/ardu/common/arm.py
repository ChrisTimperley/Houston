__all__ = ['ArmDisarmSchema']

import time

from pymavlink import mavutil

from ...configuration import Configuration
from ...action import ActionSchema, Parameter, Action
from ...specification import Specification, Idle
from ...state import State
from ...environment import Environment
from ...valueRange import DiscreteValueRange
from ..sandbox import Sandbox


class ArmDisarmSchema(ActionSchema):
    """
    Behaviours:
        Normal: if the robot is armable and is in either its 'GUIDED' or
            'LOITER' modes, the robot will become armed.
        Idle: if the conditions above cannot be met, the robot will ignore the
            command.
    """
    def __init__(self) -> None:
        name = 'arm'
        parameters = [
            Parameter('arm', DiscreteValueRange([True, False]))
        ]
        specs = [
            ArmNormally(),
            DisarmNormally(),
            Idle()
        ]
        super().__init__(name, parameters, specs)

    def dispatch(self,
                 sandbox: Sandbox,
                 action: Action,
                 state: State,
                 environment: Environment,
                 configuration: Configuration
                 ) -> None:
        vehicle = sandbox.connection
        arm_flag = 1 if action['arm'] else 0
        msg = vehicle.message_factory.command_long_encode(
            0, 0,
            mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
            0, arm_flag, 0, 0, 0, 0, 0, 0)
        vehicle.send_mavlink(msg)


class ArmNormally(Specification):
    def __init__(self) -> None:
        super().__init__('arm-normal')

    def precondition(self, action, state, environment, config):
        return action['arm'] \
            and self.is_satisfiable(state, environment, config)

    def postcondition(self,
                      action,
                      state_before,
                      state_after,
                      environment,
                      config):
        return state_after.armed

    def timeout(self, action, state, environment, config):
        return config.constant_timeout_offset + 1.0

    def is_satisfiable(self, state, environment, config):
        return state.armable and state.mode in ['GUIDED', 'LOITER']


class DisarmNormally(Specification):
    def __init__(self) -> None:
        super().__init__('disarm-normal')

    def precondition(self, action, state, environment, config):
        return not action['arm'] \
            and self.is_satisfiable(state, environment, config)

    def postcondition(self,
                      action,
                      state_before,
                      state_after,
                      environment,
                      config):
        return not state_after.armed

    def timeout(self, action, state, environment, config):
        return config.constant_timeout_offset + 1

    # TODO
    def is_satisfiable(self, state, environment, config):
        # and state['mode'] in ['GUIDED', 'LOITER']
        return state.armed
