from typing import Iterator, Tuple, Set
import argparse
import functools
import contextlib
import logging
import json
import sys
import os

import bugzoo
import boggart
import rooibos
import houston
from houston.mission import Mission
from houston.trace import CommandTrace, MissionTrace

logger = logging.getLogger('houston')  # type: logging.Logger
logger.setLevel(logging.DEBUG)

DESCRIPTION = "Builds a ground truth dataset."


def setup_logging(verbose: bool = False) -> None:
    log_to_stdout = logging.StreamHandler()
    log_to_stdout.setLevel(logging.DEBUG if verbose else logging.INFO)
    logging.getLogger('houston').addHandler(log_to_stdout)
    logging.getLogger('experiment').addHandler(log_to_stdout)


def parse_args():
    p = argparse.ArgumentParser(description=DESCRIPTION)
    p.add_argument('snapshot', help='the name of the BugZoo snapshot')
    p.add_argument('mutants', help='path to a JSON file of mutants.')
    p.add_argument('oracle', type=str, help='path to oracle trace directory.')
    p.add_argument('output', type=str,
                   help='the file to which the ground truth dataset should be written.')
    p.add_argument('--verbose', action='store_true',
                   help='increases logging verbosity')
    p.add_argument('--threads', type=int, default=1,
                   help='number of threads to use when building trace files.')
    return p.parse_args()


@contextlib.contextmanager
def launch_servers() -> Iterator[Tuple[bugzoo.Client, boggart.Client]]:
    logger.debug("launching BugZoo")
    with bugzoo.server.ephemeral(port=6060) as client_bugzoo:
        logger.debug("launching Rooibos")
        with rooibos.ephemeral_server(port=8888) as client_rooibos:
            logger.debug("launching Boggart")
            with boggart.server.ephemeral() as client_boggart:
                logger.debug("launched all services")
                yield client_bugzoo, client_boggart



def killing_mission(client_bugzoo: bugzoo.Client,
                    client_boggart: boggart.Client,
                    snapshot: bugzoo.Bug,
                    mutation: boggart.Mutation
                   ) -> Optional[Tuple[str, Mission, MissionTrace]]:

    # build trace for each mission
    pass


def build_mutant(client_bugzoo: bugzoo.Client,
                 client_boggart: boggart.Client,
                 snapshot: bugzoo.Bug,
                 mutation: boggart.Mutation
                 ) -> Iterator[bugzoo.Container]:
    """
    Provisions a BugZoo container for a given mutation.
    """
    container = None  # type: Optional[bugzoo.Container]
    mutant = client_boggart.mutate(snapshot, [mutation])
    try:
        container = client_bugzoo.containers.provision(mutant.snapshot)
        yield container
    finally:
        del client_bugzoo.containers[container.id]
    del client_boggart.mutants[mutant.uuid]


def main():
    args = parse_args()
    setup_logging(verbose=args.verbose)
    name_snapshot = args.snapshot
    fn_mutants = args.mutants
    dir_oracle = args.oracle
    fn_output = args.output
    num_threads = args.threads

    if not os.path.exists(dir_oracle):
        logger.error("oracle directory not found: %s", dir_oracle)
        sys.exit(1)

    # load the mutants
    try:
        with open(fn_mutants, 'r') as f:
            mutations = [boggart.Mutation.from_dict(jsn['mutation'])
                         for jsn in json.load(f)]
            logger.debug("loaded %d mutations from database", len(mutations))
    except Exception:
        logger.exception("failed to load mutation database: %s", fn_mutants)
        sys.exit(1)
    except FileNotFoundError:
        logger.error("mutation database file not found: %s", fn_mutants)
        sys.exit(1)

    # obtain a list of oracle traces
    trace_filenames = \
        [fn for fn in os.listdir(dir_oracle) if fn.endswith('.json')]

    # load the oracle dataset
    with launch_servers() as (client_bugzoo, client_boggart):
        snapshot = client_bugzoo.bugs[name_snapshot]
        km = functools.partial(killing_mission, client_bugzoo, client_boggart, snapshot)
        for mutation in mutations:
            

            res = killing_mission(mutant)
            fn_oracle_trace, mission, trace_mutant = res


if __name__ == '__main__':
    main()
