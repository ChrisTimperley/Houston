import thread
import time
import copy

class System(object):
    """
    Description of System.
    """


    def __init__(self, variables, schemas):
        self.__variables = variables
        self.__schemas = schemas


    def setUp(self, mission):
        """
        Responsible for appropriately configuring and launching the system,
        for a given mission.
        """
        raise NotImplementedError


    def tearDown(self, mission):
        """
        Responsible for safely closing the system, following the execution of
        a given mission.
        """
        raise NotImplementedError


    def execute(self, mission):
        """
        Executes the mission. Returns mission outcome
        """
        self.setUp(mission)
        outcomes = []
        missionPassed = True
        for action in mission.getActions():
            actionKind   = action.getKind()
            actionSchema = self.__schemas[actionKind]
            outcome = ActionOutcome(actionKind, self.getInternalState())
            # check for invariants

            result = actionSchema.satisfiedInvariants(self.__variables, action)
            if not result[0]:
                outcome.setActionReturn(False, 'Invariants : {}'.format(result[1]))
                outcome.setPostActionSystemState(self.getInternalState())
                outcomes.append(outcome)
                missionPassed = False
                break
            # check for preconditions
            result =  actionSchema.satisfiedPreconditions(self.__variables, action)
            if not result[0]:
                outcome.setActionReturn(False, 'Preconditions : {}'.format(result[1]))
                outcome.setPostActionSystemState(self.getInternalState())
                outcomes.append(outcome)
                missionPassed = False
                break
            # dispatch
            actionSchema.dispatch(action.getValues())
            print 'Doing: {}'.format(actionKind)
            # start looping till action completed or invariant violated
            while not actionSchema.satisfiedPostConditions(self.__variables, action)[0]:
                time.sleep(0.5)
                result = actionSchema.satisfiedInvariants(self.__variables, action)
                if not result[0]:
                    outcome.setActionReturn(False, 'Invariants : {}'.format(result[1]))
                    outcome.setPostActionSystemState(self.getInternalState())
                    outcomes.append(outcome)
                    missionPassed = False
                    break
            outcome.setActionReturn(True, 'Postconditions')
            outcome.setPostActionSystemState(self.getInternalState())
            outcomes.append(outcome)

        return MissionOutcome(missionPassed, outcomes)


    def getInternalState(self):
        """
        Returns a description of the current internal state of the system.

        TODO: ensure that the system is actually running!
        """
        vals = {n: v.read() for (n, v) in self.__variables.items()}
        return InternalState(vals)


class State(object):
    """
    Describes the internal or external state of the system in terms of its
    internal or external variables.
    """

    def __init__(self, values):
        """
        Constructs a description of the system state.

        :param  values: a dictionary describing the values of the state
                        variables, indexed by their names.
        """
        self.__values = copy.copy(values)


    def read(variable):
        """
        Returns the value for a given state variable
        """
        return self.__values[variable]


    def dump(self):
        """
        Prints this state to the standard output.
        """
        for variable in self.__values:
            print('Variable: {} - State: {}'.format(variable, self.read(variable)))

    def toJSON(self):
        """
        Returns a JSON description of this state.
        """
        return {
            'variables': copy.copy(self.__values)
        }

    def __str__(self):
        return str(self.toJSON())

    def __repr__(self):
        return str(self.toJSON())


class InternalState(State):
    """
    Describes the state of the system in terms of its internal state
    variables.
    """

    @staticmethod
    def fromJSON(jsn):
        """
        Constructs an internal state description from a JSON object
        """
        assert('variables' in jsn)
        assert(isinstance(jsn['variables'], dict))
        return InternalState(jsn['variables'])

class ExternalState(State):
    """
    Describes the state of the system in terms of its external state
    variables.
    """

    @staticmethod
    def fromJSON(jsn):
        """
        Constructs an external state description from a JSON object
        """
        assert('variables' in jsn)
        assert(isinstance(jsn['variables'], dict))
        return ExternalState(jsn['variables'])


class StateVariable(object):

    def __init__(self, name, getter):
        """
        Constructs a new state variable

        :param  name:   the name of this variable
        :param  type:   the type of this variable
        :param  getter: a lambda function, used to obtain the value of this variable
        """
        self.__name = name
        self.__getter = getter

    """
    Returns the name of this system variable
    """
    def name(self):
        return self.__name

    """
    Inspects the current state of this system variable
    """
    def read(self):
        return self.__getter()


class InternalStateVariable(StateVariable):
    """
    Internal variables describe the internal state of a given system.
    (i.e., they represent a system's knowledge of itself and its surroundings.)
    A user-provided lambda function is used to inspect the value of the state
    variable at any given time.
    """

    def __init__(self, name, getter):
        super(InternalStateVariable, self).__init__(name, getter)


class Environment(object):
    @staticmethod
    def fromJSON(jsn):
        """
        Constructs a description of an environment from its JSON description
        """
        assert('variables' in jsn)
        assert(isinstance(jsn['variables'], dict))
        return Enviroment(jsn['variables'])

    """
    Holds a description of an environment in which a mission should be conducted.
    """

    def __init__(self, values):
        """
        Constructs a description of a mission environment.

        :param  values: a dictionary of environment variable values, indexed
                        by the name of those variables.
        """
        self.__values = copy.copy(values)

    def read(self, variable):
        """
        Returns the value of a given environment variable.
        """
        return self.__values[variable]

    def toJSON(self):
        """
        Returns this environment description as a JSON object (i.e., a dict)
        """
        return {
            'variables': copy.copy(self.__values)
        }


class Mission(object):
    """
    A mission is represented as a sequence of actions that are carried out in
    a given environment and initial state.
    """

    @staticmethod
    def fromJSON(jsn):
        """
        Constructs a mission object from a given JSON description.
        """
        assert('environment' in jsn)
        assert('internal' in jsn)
        assert('external' in jsn)
        assert('actions' in jsn)
        assert(isinstance(actions, list))

        env = Environment.fromJSON(jsn['environment'])
        internal = InternalState.fromJSON(jsn['internal'])
        external = ExternalState.fromJSON(jsn['external'])
        actions = [a.fromJSON() for a in actions]

        return Mission(env, internal, external, actions)

    def __init__(self, environment, internal, external, actions):
        """
        Constructs a new Mission description.

        :param  environment:    a description of the environment
        :param  internal:       a description of the initial internal state
        :param  external:       a description of the initial external state
        :param  actions:        a list of actions
        """
        assert(actions != [])
        assert(isinstance(environment, Environment) and not environment is None)
        assert(isinstance(internal, InternalState) and not internal is None)
        assert(isinstance(external, ExternalState) and not external is None)

        self.__environment = environment
        self.__internal = internal
        self.__external = external
        self.__actions = actions

    # TODO: make immutable
    def getEnvironment(self):
        return self.__environment

    # TODO: make immutable
    def getInitialInternalState(self):
        return self.__internal

    # TODO: make immutable
    def getInitialExternalState(self):
        return self.__external

    # TODO: make immutable
    def getActions(self):
        # TODO: returning the original list might be dangerous? We may want to
        #       pass a copy, instead.
        return self.__actions

    def toJSON(self):
        """
        Returns a JSON description of this mission.
        """
        return {
            'environment': self.__environment.toJSON(),
            'internal': self.__internal.toJSON(),
            'external': self.__external.toJSON(),
            'actions': [a.toJSON() for a in self.__actions]
        }

class MissionOutcome(object):

    def __init__(self, passFail, outcomes):
        """
        Constructs a MissionOutcome object.

        :param  passFail    holds the outcome of the missions. True for passed
                            and False for failed.
        :param  outcomes    a list that cointains the ActionOutcomes for the
                            mission.
        """
        self.__passFail  = passFail
        self.__outcomes  = outcomes

    def toJSON(self):
        """
        Returns a JSON description of the mission outcome.
        """
        return {
            'passed': self.__passFail,
            'actions': self.__outcomes
        }


class ActionOutcome(object):
    def __init__(self, action, preActionSytemSate):

        self.__action                     = action
        self.__preActionSytemSate         = preActionSytemSate
        self.__actionReturn               = False
        self.__postActionSystemState      = None

    def toJSON(self):
        return {
            'action': self.__action,
            'outcome': self.__actionReturn,
            'preActionSystemSate': self.__preActionSytemSate,
            'postActionSystemState': self.__postActionSystemState}

    def setPostActionSystemState(self, postActionSystemState):
        self.__postActionSystemState  = postActionSystemState

    def setActionReturn(self, actionReturn, statetype):
        self.__actionReturn = actionReturn


class Action(object):
    @staticmethod
    def fromJSON(jsn):
        """
        Constructs an Action object from its JSON description.
        """
        assert('kind' in jsn)
        assert('parameters' in jsn)
        return Action(jsn['kind'], jsn['parameters'])

    def __init__(self, kind, values):
        """
        Constructs an Action description.

        :param  kind    the name of the schema to which the action belongs
        :param  values  a dictionary of parameter values for the action
        """
        assert(isinstance(kind, str))
        assert(isinstance(values, dict))
        self.__kind = kind
        self.__values = copy.copy(values)

    def getKind(self):
        return self.__kind

    def getValue(self, value):
        return self.__values[value]

    def getValues(self):
        return copy.copy(self.__values)

    def toJSON(self):
        """
        Returns a JSON description of a given Action.
        """
        return {
            'kind': self.__kind,
            'parameters': self.getValues()
        }


class ActionSchema(object):
    """
    Action schemas are responsible for describing the kinds of actions that
    can be performed within a given system. Action schemas describe actions
    both syntactically, in terms of parameters, and semantically, in terms of
    preconditions, postconditions, and invariants.
    """

    def __init__(self, name, parameters, precondition, invariants, postconditions):
        self.__name           = name
        self.__parameters     = parameters
        self.__preconditions   = precondition
        self.__invariants     = invariants
        self.__postconditions = postconditions


    def dispatch(self, action):
        """
        Responsible for invoking an action belonging to this schema.

        :param  action  an Action belonging to this schema
        """
        raise UnimplementedError


    def satisfiedPostConditions(self, systemVariables, parameters):
        #print 'Doing postconditions. Action: {}'.format(parameters.getKind())
        postconditionsFailed = []
        success               = True
        for postcondition in self.__postconditions:
            if not postcondition.check(systemVariables, parameters.getValues()):
                postconditionsFailed.append(postcondition.getName())
                success = False

        return (success, postconditionsFailed)

    def satisfiedPreconditions(self, systemVariables, parameters):
        #print 'Doing precondition. Action: {}'.format(parameters.getKind())
        preconditionsFailed = []
        success              = True
        for precondition in self.__preconditions:
            if not precondition.check(systemVariables, parameters.getValues()):
                preconditionsFailed.append(precondition.getName())
                success = False
        return (success, preconditionsFailed)

    def satisfiedInvariants(self, systemVariables, parameters):
        #print 'Doing invariants. Action: {}'.format(parameters.getKind())
        invariantsFailed    = []
        success             = True
        for invariant in self.__invariants:
            if not invariant.check(systemVariables, parameters.getValues()):
                invariantsFailed.append(invariant.getName())
                success = False
        return (success, invariantsFailed)


"""
Hello.
"""
class Predicate(object):

    def __init__(self, name, predicate):
        self.__name = name
        self.__predicate = predicate


    def check(self, system_variables, parameters):
        return self.__predicate(system_variables, parameters)


"""
Hello.
"""
class Invariant(Predicate):
    def __init__(self, name, description, predicate):
        super(Invariant, self).__init__(name, predicate)
        self.__name = name
        self.__description = description

    def getName(self):
        return self.__name

"""
Hello.
"""
class Postcondition(Predicate):
    def __init__(self, name, description, predicate):
        super(Postcondition, self).__init__(name, predicate)
        self.__name = name
        self.__description = description

    def getName(self):
        return self.__name

"""
Hello.
"""
class Precondition(Predicate):
    def __init__(self, name, description, predicate):
        super(Precondition, self).__init__(name, predicate)
        self.__name = name
        self.__description = description

    def getName(self):
        return self.__name


"""
Hello.
"""
class Parameter(object):
    """docstring for ."""
    def __init__(self, typ, value, description):
        self.__type = typ
        self.__value = value
        self._description = description


    def get_value():
        return self.__value
