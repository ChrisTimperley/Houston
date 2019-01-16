from typing import Iterator, Tuple, Set, List, Dict, Any, Optional, Type
import argparse
import functools
import contextlib
import attr
import logging
import json
import sys
import os

import bugzoo
import boggart
import rooibos
import houston
from bugzoo import BugZoo as BugZooDaemon
from houston import System
from houston.mission import Mission
from houston.trace import CommandTrace, MissionTrace
from houston.ardu.copter import ArduCopter

from compare_traces import load_file as load_traces_file
from compare_traces import matches_ground_truth

logger = logging.getLogger('houston')  # type: logging.Logger
logger.setLevel(logging.DEBUG)

DESCRIPTION = "Builds a ground truth dataset."


@attr.s
class DatabaseEntry(object):
    diff = attr.ib(type=str)
    fn_oracle = attr.ib(type=str)
    mission = attr.ib(type=Mission)
    trace_mutant = attr.ib(type=MissionTrace)

    def to_dict(self) -> Dict[str, Any]:
        return {'diff': self.diff,
                'mission': self.mission.to_dict(),
                'oracle': self.fn_oracle,
                'trace': self.trace_mutant.to_dict()}


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


def process_mutation(system: Type[System],
                     daemon_bugzoo: BugZooDaemon,
                     snapshot: bugzoo.Bug,
                     trace_filenames: List[str],
                     diff: str
                     ) -> Optional[DatabaseEntry]:
    patch = bugzoo.Patch.from_unidiff(diff)
    bz = daemon_bugzoo
    sandbox_cls = system.sandbox
    container = None  # type: Optional[bugzoo.Container]
    try:
        container = bz.containers.provision(snapshot)
        logger.debug("built container")
        if not bz.containers.patch(container, patch):
            logger.error("failed to patch using diff: %s", diff)
            return None
        if not bz.containers.build(container).successful:
            logger.error("failed to build mutant: %s", diff)
            return None

        def obtain_trace(mission: houston.Mission) -> MissionTrace:
            args = [bz, container, mission.initial_state,
                    mission.environment, mission.configuration]
            with sandbox_cls.for_container(*args) as sandbox:
                return sandbox.run_and_trace(mission.commands)

        for fn_trace in trace_filenames:
            logger.debug("evaluating oracle trace: %s", fn_trace)
            mission, oracle_traces = load_traces_file(fn_trace)
            trace_mutant = obtain_trace(mission)
            return DatabaseEntry(mutation, diff, fn_trace, mission, trace_mutant)

    except Exception:
        logger.exception("failed to obtain data for mutant: %s", diff)
        return None
    except houston.exceptions.NoConnectionError:
        logger.error("mutant resulted in crash")
        return None
    finally:
        del bz.containers[container.id]
    return None


def main():
    args = parse_args()
    setup_logging(verbose=args.verbose)
    name_snapshot = args.snapshot
    fn_mutants = args.mutants
    dir_oracle = args.oracle
    fn_output = args.output
    num_threads = args.threads
    system = ArduCopter

    if not os.path.exists(dir_oracle):
        logger.error("oracle directory not found: %s", dir_oracle)
        sys.exit(1)

    # load the mutant diffs
    try:
        with open(fn_mutants, 'r') as f:
            diffs = [jsn['diff'] for jsn in json.load(f)]
            logger.debug("loaded %d diffs from database", len(diffs))
    except Exception:
        logger.exception("failed to load mutation database: %s", fn_mutants)
        sys.exit(1)
    except FileNotFoundError:
        logger.error("mutation database file not found: %s", fn_mutants)
        sys.exit(1)

    # FIXME for the sake of expediting things
    diffs = diffs[:5]

    # obtain a list of oracle traces
    trace_filenames = \
        [fn for fn in os.listdir(dir_oracle) if fn.endswith('.json')]
    trace_filenames = [os.path.join(dir_oracle, fn) for fn in trace_filenames]

    # launch the BugZoo daemon
    daemon_bugzoo = bugzoo.BugZoo()

    # build the database
    db_entries = []  # type: List[DatabaseEntry]
    snapshot = daemon_bugzoo.bugs[name_snapshot]
    process = functools.partial(process_mutation,
                                system,
                                daemon_bugzoo,
                                snapshot,
                                trace_filenames)
    db_entries = [process(diff) for diff in diffs]
    db_entries = [e for e in db_entries if e]

    # save to disk
    logger.info("finished constructing evaluation dataset.")
    logger.debug("saving evaluation dataset to disk.")
    jsn = {
        'oracle-directory': dir_oracle,
        'snapshot': name_snapshot,
        'entries': [e.to_dict() for e in db_entries]
    }
    with open(fn_output, 'w') as f:
        json.dump(jsn, f, indent=2)
    logger.info("saved evaluation dataset to disk")


if __name__ == '__main__':
    main()
