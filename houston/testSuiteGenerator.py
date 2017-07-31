import json
import random

MAX_MISSIONS = 20
MAX_ACTIONS  = 20
'''
PISF: Parameter-Initial-State-Format. This is used to bound parameter values.
'''

class TestSuiteGenerator(object):

    def __init__(self, pisf, actionSchemas, fileOutput):
        self.__pisf          = pisf
        self.__actionSchemas = actionSchemas
        self.__fileOutput    = fileOutput

    def generateRandomTest(self):
        tsd = TestSuiteDumper(self.__fileOutput)
        for numMission in range(MAX_MISSIONS):
            tempMission = {}
            tempMission['environment'] = self.populateInitialState('environment')
            tempMission['initialInternalState'] = self.populateInitialState('initialInternalState')
            tempMission['initialExternalState'] = self.populateInitialState('initialExternalState')
            tempMission['actions'] = []
            for numAction in range(MAX_ACTIONS):
                action, schema = random.choice(list(self.__actionSchemas.items()))
                tempMission['actions'].append(self.populateAction(action, schema))
            tsd.appendMission(tempMission)
        tsd.dumpMissionJSON()


    def populateInitialState(self, state):
        initialState = {'variables': {}}
        PISFState = self.__pisf[state]
        if not PISFState:
            return initialState

        for variable in PISFState:
            if len(PISFState[variable]) > 1:
                minVal = PISFState[variable]['min']
                maxVal = PISFState[variable]['max']
                initialState['variables'][variable] = random.uniform(minVal, maxVal)
            else:

                randomChoice = random.choice(PISFState[variable])
                initialState['variables'][variable] = randomChoice

        return initialState

    def populateAction(self, action, schema):
        actionParameters = schema.getParameters()
        populatedAction = {action:{}}
        if not actionParameters:
            return populatedAction
        for parameterObject in actionParameters:
            parameter = parameterObject.getType()
            if parameter not in self.__pisf['parameters']:
                exit()
            if len(self.__pisf['parameters'][parameter])>1:
                minVal = self.__pisf['parameters'][parameter]['min']
                maxVal = self.__pisf['parameters'][parameter]['max']
                populatedAction[action][parameter] = random.uniform(minVal, maxVal)
            else:
                randomChoice = random.choice(
                    self.__pisf['parameters'][parameter]["options"])
                populatedAction[action][parameter] = randomChoice
        return populatedAction


class TestSuiteDumper(object):
    def __init__(self, testSuiteName):
        self.__testSuiteName = testSuiteName
        self.__missions      = {}

    def appendMission(self, missionInput):
        if len(self.__missions) == 0:
            self.__missions[0] = missionInput
        else:
            self.__missions[len(self.__missions)] = missionInput

    def dumpMissionJSON(self):
        with open(self.__testSuiteName, 'w') as file:
            json.dump({'testSuite': self.__missions}, file, sort_keys=True,
                indent=4, separators=(',', ': '))
