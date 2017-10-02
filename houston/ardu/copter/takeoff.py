import time
import math

from houston.action import ActionSchema, Parameter, Action
from houston.branch import Branch, IdleBranch
from houston.valueRange import ContinuousValueRange


class TakeoffSchema(ActionSchema):
    """docstring for TakeoffActionSchema.
    
    Branches:
        Normally:
        Idle:
    """
    def __init__(self):
        parameters = [
            Parameter('altitude', ContinuousValueRange(0.3, 100.0))
        ]
        branches = [
            TakeoffNormally(self),
            IdleBranch(self)
        ]

        super(TakeoffSchema, self).__init__('takeoff', parameters, branches)


    def dispatch(self, system, action, state, environment):
        from pymavlink import mavutil
        vehicle = system.vehicle
        msg = vehicle.message_factory.command_long_encode(
            0, 0,
            mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
            0, 1, 0, 0, 0, 0, 0, action['altitude'])
        vehicle.send_mavlink(msg)


class TakeoffNormally(Branch):
    def __init__(self, system):
        super(TakeoffNormally, self).__init__("normal", system)


    def timeout(self, system, action, state, environment):
        timeout = action['altitude'] * system.time_per_metre_travelled
        timeout += system.constant_timeout_offset
        return timeout


    def postcondition(self, system, action, state_before, state_after, environment):
        return  system.variable('longitude').eq(state_before['longitude'], state_after['longitude']) and \
                system.variable('latitude').eq(state_before['latitude'], state_after['latitude']) and \
                system.variable('altitude').eq(state_after['altitude'], action['altitude']) and \
                system.variable('vz').eq(state_after['vz'], 0.0)


    def precondition(self, system, action, state, environment):
        return  state['armed'] and \
                state['mode'] == 'GUIDED' and \
                system.variable('altitude').lt(state['altitude'], 0.3)
                # TODO further check; CT: for what?


    def is_satisfiable(self, system, state, environment):
        return self.precondition(system, None, state, environment)


    def generate(self, system, state, env, rng):
        return self.schema.generate(rng)
