import time

from houston.action import ActionSchema, Parameter, Action
from houston.branch import Branch, IdleBranch
from houston.state import Estimator, FixedEstimator
from houston.valueRange import DiscreteValueRange


try:
    import dronekit
except ImportError:
    pass


class SetModeSchema(ActionSchema):
    """
    docstring for SetModeActionSchema

    Branches:

        Guided:
        Loiter:
        RTL:
        Land:
        Idle:
    """
    def __init__(self):
        parameters = [
            Parameter('mode', DiscreteValueRange(['GUIDED', 'LOITER', 'RTL', 'LAND']))
        ]
        branches = [
            SetModeGuided(self),
            SetModeLoiter(self),
            SetModeRTL(self),
            SetModeLand(self),
            IdleBranch(self)
        ]

        super(SetModeSchema, self).__init__('setmode', parameters, branches)

    # these send commands are all almost identical?    
    def sendRTL(self, vehicle):
        msg = vehicle.message_factory.command_long_encode(
            0, 0,
            mavutil.mavlink.MAV_CMD_NAV_RETURN_TO_LAUNCH,
            0,
            0,
            0,
            0,
            0,
            0, 0, 0)
        vehicle.send_mavlink(msg)


    def sendLAND(self, vehicle):
        msg = vehicle.message_factory.command_long_encode(
            0, 0,
            mavutil.mavlink.MAV_CMD_NAV_LAND,
            0,
            0,
            0,
            0,
            0,
            0, 0, 0)
        vehicle.send_mavlink(msg)


    def sendLOITER(self, vehicle):
        msg = vehicle.message_factory.command_long_encode(
            0, 0,
            mavutil.mavlink.MAV_CMD_NAV_LOITER_UNLIM,
            0,    #confirmation
            0,    # param 1
            0,    # param 2,
            0,    # param 3,
            0,    # param 4,
            0, 0, 0)    # param 5 ~ 7 not used
            # send command to vehicle
        vehicle.send_mavlink(msg)


    def dispatch(self, system, action, state, environment):
        vehicle = system.getVehicle()
        vehicleMode = dronekit.VehicleMode(action.read('mode'))

        if action.read('mode') == 'RTL':
            self.sendRTL(vehicle)
            currentAlt = vehicle.location.global_relative_frame.alt
            currentLat  = vehicle.location.global_relative_frame.lat
            currentLon = vehicle.location.global_relative_frame.lon
            toLocation = (state.read('homeLatitude'), state.read('homeLongitude'))
            fromLocation = (currentLat, currentLon)

            while not vehicle.mode == vehicleMode:
                time.sleep(0.2)

            while geopy.distance.great_circle(fromLocation, toLocation).meters > 0.3 and \
                currentAlt > 0.1:
                time.sleep(0.2)
                currentLat = vehicle.location.global_relative_frame.lat
                currentLon = vehicle.location.global_relative_frame.lon
                currentAlt = vehicle.location.global_relative_frame.alt

            while vehicle.armed:
                time.sleep(0.2)

        elif action.read('mode') == 'LAND':
            self.sendLAND(vehicle)
            currentAlt = vehicle.location.global_relative_frame.alt

            while not vehicle.mode == vehicleMode:
                time.sleep(0.2)

            while currentAlt > 0.1:
                time.sleep(0.2)
                currentAlt = vehicle.location.global_relative_frame.alt

            while vehicle.armed:
                time.sleep(0.2)

        elif action.read('mode') == 'LOITER': # TODO as we add more modes this would have to change
            self.sendLOITER(vehicle)
            while not vehicle.mode == vehicleMode:
                time.sleep(0.1)

        elif action.read('mode') == 'GUIDED':
            vehicle.mode = vehicleMode
            while not vehicle.mode == vehicleMode:
                time.sleep(0.1)

        else:
            raise Exception("unexpected mode")


class SetModeLand(Branch):
    """
    Should describe precondition, postcondition, invariants, and method for
    calculating a suitable timeout.
    """
    def __init__(self, schema):
        estimators = [
            FixedEstimator('mode', 'LAND'),
            FixedEstimator('armed', False),
            Estimator('latitude', lambda action, state, env: state.read('latitude')),
            Estimator('longitude', lambda action, state, env: state.read('longitude')),
            Estimator('altitude', lambda action, state, env: 0.0)
        ]
        super(SetModeLand, self).__init__('land', schema, estimators)


    def computeTimeout(self, action, state, environment):
        timeout = (state.read('altitude') * TIME_PER_METER_TRAVELED) + CONSTANT_TIMEOUT_OFFSET
        return timeout


    def isApplicable(self, action, state, environment):
        return action.read('mode') == 'LAND'


    def isSatisfiable(self, state, environment):
        return True


    def generate(self, state, environment, rng):
        return Action(self.getSchemaName(), {'mode': 'LAND'})


class SetModeGuided(Branch):
    """
    Description.
    """
    def __init__(self, schema):
        estimators = [
            FixedEstimator('mode', 'GUIDED')
        ]
        super(SetModeGuided, self).__init__('guided', schema, estimators)


    def computeTimeout(self, action, state, environment):
        return CONSTANT_TIMEOUT_OFFSET


    def isApplicable(self, action, state, environment):
        return action.read('mode') == 'GUIDED'


    def isSatisfiable(self, state, environment):
        return True


    def generate(self, state, environment, rng):
        return Action(self.getSchemaName(), {'mode': 'GUIDED'})



class SetModeLoiter(Branch):
    """
    Description.
    """
    def __init__(self, schema):
        estimators = [
            FixedEstimator('mode', 'LOITER')
        ]
        super(SetModeLoiter, self).__init__('loiter', schema, estimators)


    def computeTimeout(self, action, state, environment):
        return CONSTANT_TIMEOUT_OFFSET


    def isApplicable(self, action, state, environment):
        return action.read('mode') == 'LOITER'


    def isSatisfiable(self, state, environment):
        return True


    def generate(self, state, environment, rng):
        return Action(self.getSchemaName(), {'mode': 'LOITER'})


class SetModeRTL(Branch):
    """
    Description.
    """
    def __init__(self, schema):
        estimators = [
            FixedEstimator('mode', 'RTL'),
            Estimator('armed', lambda action, state, env: state.read('armed') if state.read('altitude') < 0.3 else False),
            Estimator('latitude', lambda action, state, env: state.read('homeLatitude')),
            Estimator('longitude', lambda action, state, env: state.read('homeLongitude')),
            Estimator('altitude', lambda action, state, env: 0.0)
        ]
        super(SetModeRTL, self).__init__('rtl', schema, estimators)


    def computeTimeout(self, action, state, environment):
        fromLocation = (state.read('latitude'), state.read('longitude'))
        toLocation   = (state.read('homeLatitude'), state.read('homeLongitude'))
        # Distance from current coor to home coor
        totalDistance = geopy.distance.great_circle(fromLocation, toLocation).meters
        # Land times and adjustment time for altitude
        totalLandTime = (state.read('altitude') * TIME_PER_METER_TRAVELED)
        totalGoUpDownTime = (math.fabs(10 - state.read('altitude')) * TIME_PER_METER_TRAVELED)
        # Land and adjustment time for altitude added
        goUpDownAndLandTime = totalGoUpDownTime + totalLandTime
        # Go to home lat and lon time travel.
        gotoTotalTime = (totalDistance * TIME_PER_METER_TRAVELED)
        # Total timeout
        timeout = totalGoUpDownTime + gotoTotalTime + CONSTANT_TIMEOUT_OFFSET
        return timeout


    def isApplicable(self, action, state, environment):
        return action.read('mode') == 'RTL'


    def isSatisfiable(self, state, environment):
        return True


    def generate(self, state, environment, rng):
        return Action(self.getSchemaName(), {'mode': 'RTL'})
