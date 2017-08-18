import copy
import random
import timeit
import houston
import system

from multiprocessing.pool import ThreadPool

from mission import Mission, Action

class ResourceUsage(object):
    """
    Simple data structure used to maintain track of what resources have been
    consumed over the course of a bug detection trial.
    """
    def __init__(self):
        self.numMissions = 0
        self.runningTime = 0.0


    def toJSON(self):
        return {
            'numMissions': self.numMissions,
            'runningTime': self.runningTime
        }


class ResourceLimits(object):
    """
    A convenience class used to impose limits on the bug detection process.
    """
    def __init__(self, numMissions = None, numMaxActions = None, runningTime = None):
        self.__numMissions = numMissions
        self.__numMaxActions  = numMaxActions
        self.__runningTime = runningTime


    def reached(self, usage):
        if self.reachedMissionLimit(usage.numMissions):
            return True
        if self.reachedTimeLimit(usage.runningTime):
            return True
        print usage.runningTime
        return False


    def getNumMissions(self):
        return self.__numMissions


    def getMaxNumActions(self):
        return self.__numMaxActions


    def reachedMissionLimit(self, numMissions):
        return  self.__numMissions is not None and \
                    numMissions >= self.__numMissions


    def reachedTimeLimit(self, runningTime):
        return  self.__runningTime is not None and \
                    runningTime >= self.__runningTime


    def toJSON(self):
        return {
            'numMissions': self.__numMissions,
            'runningTime': self.__runningTime
        }



class BugDetectorSummary(object):
    def __init__(self, history, outcomes, failures, resourceUsage, resourceLimits):
        """
        Constructs a summary of a bug detection process.

        :params resourceUsage:  a description of the resources consumed during \
                    the bug detection process.
        :params resourceLimits: a description of the resources limits that \
                    were imposed during the bug detection process.
        """
        assert (isinstance(resourceUsage, ResourceUsage) and resourceUsage is not None)
        assert (isinstance(resourceLimits, ResourceLimits) and resourceLimits is not None)
        assert (isinstance(history, list) and history is not None)
        assert (isinstance(outcomes, dict) and outcomes is not None)
        assert (isinstance(failures, set) and failures is not None)
        assert (all(isinstance(m, Mission) for m in failures))

        self.__history = history
        self.__outcomes = outcomes
        self.__failures = failures
        self.__resourceUsage = copy.copy(resourceUsage)
        self.__resourceLimits = resourceLimits


    def toJSON(self):
        """
        Transforms this bug detection summary into a JSON format.
        """
        resources = {
            'used': self.__resourceUsage.toJSON(),
            'limits': self.__resourceLimits.toJSON()
        }

        history = [(m, self.__outcomes[m]) for m in self.__history]
        history = [{'mission': m.toJSON(), 'outcome': o.toJSON()} for (m, o) in history]


        failures = [(m, self.__outcomes[m]) for m in self.__failures]
        failures = [{'mission': m.toJSON(), 'outcome': o.toJSON()} for (m, o) in failures]

        summary = {
            'resources': resources,
            'history': history,
            'failures': failures
        }

        return {'summary': summary}


class BugDetector(object):
    """
    Bug detectors are responsible for finding bugs in a given system under test.
    """
    def __init__(self, threads = 1, actionGenerators = []):
        assert (isinstance(threads, int) and threads is not None)
        assert (threads >= 1)
        assert (isinstance(actionGenerators, list) and actionGenerators is not None)
        assert (all(isinstance(g, system.ActionGenerator) for g in actionGenerators))

        # transform the list of generators into a dictionary, indexed by the
        # name of the associated action schema
        self.__threads = threads
        self.__actionGenerators = {}
        for g in actionGenerators:
            name = g.getSchemaName()
            assert not (name in self.__actionGenerators)
            self.__actionGenerators[name] = g


    def prepare(self, systm, image, resourceLimits):
        """
        Prepares the state of the bug detector immediately before beginning a
        bug detection trial.
        """
        self.__systm = systm
        self.__image = image
        self.__containers = []
#        self.__containers = \
#            [houston.createContainer(systm, image) for i in range(self.__threads)]
        self.__resourceUsage = ResourceUsage()
        self.__resourceLimits = resourceLimits
        self.__startTime = timeit.default_timer()
        self.__history = []
        self.__outcomes = {}
        self.__failures = set()


    def cleanup(self):
        """
        Cleans up the state of this bug detector at the end of a bug detection
        trial.
        """
        for container in self.__containers:
            container.destroy()

        self.__containers = []


    def exhausted(self):
        """
        Used to determine whether the resource limit for the current bug
        detection session has been hit.
        """
        return self.__resourceLimits.reached(self.__resourceUsage)


    def detect(self, systm, image, resourceLimits):
        """

        :param      systm: the system under test
        :param      image: the name of the Dockerfile that should be used to \
                        containerise the system under test
        :param      resourceLimits: a description of the resources available \
                        to the detection process, given as a ResourceLimits \
                        object

        :returns    a summary of the detection process in the form of a \
                    BugDetectionSummary object
        """
        self.prepare(systm, image, resourceLimits)
        try:
            self.run(systm)
            summary = BugDetectorSummary(self.__history,
                                         self.__outcomes,
                                         self.__failures,
                                         self.__resourceUsage,
                                         self.__resourceLimits)
            return summary
        finally:
            self.cleanup()


    def run(self, systm):
        raise NotImplementedError


    def getMaxNumActions(self):
        return self.__resourceLimits.getMaxNumActions()


    def generateAction(self, schema, currentState, env):
        """
        Generates an instance of a given action schema at random.
        """
        name = schema.getName()
        if name in self.__actionGenerators:
            g = self.__actionGenerators[name]
            return g.generate(currentState, env)

        return schema.generate()


    def getNumThreads(self):
        """
        Returns the number of threads specified.
        """
        return self.__threads


    def getGenerator(self, schema):
        """
        Returns an available generator for a given action schema if there are
        non then it returns None.
        """
        name = schema.getName()
        if name in self.__actionGenerators:
            return self.__actionGenerators[name]
        return None


    def executeMissions(self, missions):
        # if we've been given more missions than we can execute, trim the list
        missions = list(missions)
        missionLimit = self.__resourceLimits.getNumMissions()
        if missionLimit is not None:
            missionsLeft = missionLimit - self.__resourceUsage.numMissions
            missions = missions[:min(len(missions), missionsLeft)]

        # use a thread pool to distribute the execution
        tPool = ThreadPool(self.__threads)
        outcomes = tPool.map(lambda m: (m, self.executeMission(m)), missions)
        for (mission, outcome) in outcomes:
            self.recordOutcome(mission, outcome)

        # update resource usage
        self.__resourceUsage.numMissions += len(missions)
        self.__resourceUsage.runningTime = \
            timeit.default_timer() - self.__startTime


    def executeMission(self, mission):
        # TODO: temporary!
        print("executing mission...")
        container = houston.createContainer(self.__systm, self.__image)
        try:
            outcome = container.execute(mission)
            print("finished mission!")
            return outcome
        finally:
            container.destroy()


    def recordOutcome(self, mission, outcome):
        """
        Records the outcome of a given mission. The mission is logged to the
        history, and its outcome is stored in the outcome dictionary. If the
        mission failed, the mission is also added to the set of failed
        missions.
        """
        self.__history.append(mission)
        self.__outcomes[mission] = outcome

        if outcome.failed():
            self.__failures.add(mission)


class IncrementalBugDetector(BugDetector):
    def __init__(self, initialState, env, threads = 1, actionGenerators = []):
        super(IncrementalBugDetector, self).__init__(threads, actionGenerators)
        self.__initialState = initialState
        self.__env = env


    def getInitialState(self):
        return self.__initialState


    def getEnvironment(self):
        return self.__env


    def prepare(self, systm, image, resourceLimits):
        super(IncrementalBugDetector, self).prepare(systm, image, resourceLimits)

        # seed the pool
        m = Mission(self.getEnvironment(), self.getInitialState(), [])
        self.__pool = set([m])
        self.__endStates = {m: self.getInitialState()}

        # initialise the tabu list
        self.__tabu = set()


    def recordOutcome(self, mission, outcome):
        super(IncrementalBugDetector, self).recordOutcome(mission, outcome)
        self.__endStates[mission] = outcome.getEndState()

        if not outcome.failed(): # TODO: update tabu list
                self.__pool.add(mission)


    def run(self, systm):
        while not self.exhausted():
            self.runGeneration(systm)


    def generateAction(schema, state, env):
        generator = self.getGenerator(schema)

        if generator is None:
            return schema.generate()
        return generator.generateActionWithState(state, env)


    def runGeneration(self, systm):
        schemas = systm.getActionSchemas().values()
        maxNumActions = self.getMaxNumActions()
        N = 10

        if maxNumActions is not None:
            parents = [p for p in self.__pool if p.size() < maxNumActions]
        else:
            parents = self.__pool

        parents = [random.sample(parents, 1)[0] for i in range(N)]
        children = set()

        # generate candidate missions using the selected parents
        # discard any missions that belong to the tabu list
        for parent in parents:
            schema = random.choice(schemas)
            env = parent.getEnvironment()
            currentState = self.__endStates[parent]
            action = self.generateAction(schema, currentState, env)


            actions = parent.getActions() + [action]

            # TODO: implement tabu list
            child = Mission(env, parent.getInitialState(), actions)
            children.add(child)

        self.executeMissions(children)


class RandomBugDetector(BugDetector):
    def __init__(self, initialState, env, threads = 1, actionGenerators = []):
        super(RandomBugDetector, self).__init__(threads, actionGenerators)
        self.__initialState = initialState
        self.__env = env


    def run(self, systm):
        while not self.exhausted():
            self.runGeneration(systm)

   def generateAction(self, schema):
       generator = self.getGenerator(schema)
       if generator is None:
           return schema.generate() # CAN'T TAKE STATE
       return generator.generateActionWithoutState(self.__env)


    def runGeneration(self, systm):
        schemas = systm.getActionSchemas().values()
        maxNumActions = self.getMaxNumActions()
        env = self.__env
        initialState = self.__initialState

        if maxNumActions is None:
            maxNumActions = 10 #TODO default.

        bffr = []
        for _ in range(self.getNumThreads()): # TODO add getNumThreads() to BugDetector
            actions = []
            for _ in range(random.randint(1, maxNumActions))
                schema = random.choice(schemas)
                actions.append(self.generateAction(schema))
            mission = Mission(env, initialState, actions)
            bffr.append(mission)

        self.executeMissions(bffr)


    def recordOutcome(self, mission, outcome):
        super(IncrementalBugDetector, self).recordOutcome(mission, outcome)
        self.__endStates[mission] = outcome.getEndState()

        if not outcome.failed():
                self.__pool.add(mission)
