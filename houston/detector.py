import copy

class ResourceUsage(object):

    def __init__(self):
        self.__numMissions = 0


class ResourceLimits(object):
    """
    A convenience class used to impose limits on the bug detection process.
    """
    def __init__(self, numMissions = None):
        self.__numMissions = numMissions


    def reached(self, usage):
        return False


    def reachedMissionLimit(self, numMissions):
        return  self.__numMissions is not None \
                    or numMissions >= self.__numMissions


class BugDetector(object):
    """
    Bug detectors are responsible for finding bugs in a given system under test.
    """
    def __init__(self):
        pass

    
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
        resourceUsage = ResourceUsage()


        summary = BugDetectionSummary(resourceUsage, resourceLimits)
        return summary


class BugDetectionSummary(object):
    def __init__(self, resourceUsage, resourceLimits):
        """
        Constructs a summary of a bug detection process.

        :params resourceUsage:  a description of the resources consumed during \
                    the bug detection process.
        :params resourceLimits: a description of the resources limits that \
                    were imposed during the bug detection process.
        """
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
        summary = {
            'resources': resources
        }
        return {'summary': summary}


class IncrementalBugDetector(BugDetector):
    
    def __init__(self, initialState, actionGenerators):
        self.__initialState = initialState
        self.__actionGenerators = actionGenerators


    def getInitialState(self):
        return self.__initialState


class RandomBugDetector(BugDetector):
    pass


class RandomDirectedBugDetector(BugDetector):
    
    def generate(self):
        schemas = list(self.getSystem().getSchemas().values())

        # TODO: an ordered dictionary of mission outcomes
        outcomes = {}

        # the set of pruned mission paths
        tabu = set()

        # the set of failing missions, believed to be indicate of an
        # underlying fault
        failures = {}

        # seed the initial contents of the pool
        pool = set([Mission(self.__initialState, [])])

        # sample N missions with replacement from the pool
        N = 10
        parents = random.sample(pool, N)
        children = set()

        # generate candidate missions using the selected parents
        # discard any missions that belong to the tabu list
        for parent in parents:
            schema = random.choice(schemas)
            action = self.generateAction(schema)

            child = Mission(parent.getContext(), parent.getActions() + [action]) # TODO: Mission::getContext

            if child in tabu: # TODO: optimise (via hashing)
                continue

            children.append(child)

        # evaluate each of the missions (in parallel, using a thread pool)
        results = {child: cntr.execute(child) for child in children}

        # process the results for each child
        for (child, outcome) in results.items():
            if outcome.failed():
                # if the last action failed, mark the mission as fault-revealing
                if outcome.lastActionFailed():
                    failures[child] = outcome
                    tabu[child] = outcome

                # if an earlier action failed, add the failing segment of the
                # mission to the tabu list
                else:
                    blah

            # if the test was successful, add it to the pool
            else:
                pool[child] = outcome
             
        
    # TODO: implement via ActionGenerator
    def generateAction(self, schema):
        pass
