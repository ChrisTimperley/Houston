from typing import List, Set
import random

import bugzoo
import boggart
from houston.mission import Mission
from houston import BehaviorModel

BUGZOO_IMAGE = ''


def obtain_trace(container: bugzoo.Container,
                 mission: Mission
                 ) -> MissionTrace:
    pass


def generate_mutations(client_bugzoo: bugzoo.Client,
                       client_boggart: boggart.Client,
                       snapshot: bugzoo.Bug,
                       num_mutations: int
                       ) -> List[Mutation]:
    """
    Generates the required number of behavioral mutations.
    """
    output = []  # type: List[boggart.Mutation]

    # TODO specify the mutation operators that may be used
    operators = set()

    # TODO determine the set of files that can be mutated
    files = set()

    # generate and shuffle all possible mutations
    q = []  # type: List[Mutant]
    get_mutations_in_file = lambda fn: \
        client_boggart.mutations(snapshot, fn, language=boggart.Language.CPP)
    for fn in mutable_files:
        q += get_mutations_in_file(fn)
    q = random.shuffle(q)

    # TODO retain the behavioral mutants
    # - throw it away if it doesn't build
    # - throw it away if the program crashes
    # - throw away if trace is same as oracle
    pass


def evaluate_on_mutation(client_bugzoo: bugzoo.Client,
                         client_boggart: boggart.Client,
                         snapshot: bugzoo.Bug,
                         mutation: boggart.Mutation
                         ) -> None:
    mutant_snapshot = client_boggart.mutate(snapshot, [mutation])
    container = None

    # obtain the trace
    was_killed = any(killed(m) for m in missions)

    # we don't need to ensure that this line is called -- all mutants are
    # destroyed when the boggart server is closed.
    del client_boggart.mutants[mutant_snapshot.uuid]

    return was_killed


def evaluate(client_bugzoo: bugzoo.Client,
             client_boggart: boggart.Client,
             snapshot: bugzoo.Bug
             ) -> None:
    pass
