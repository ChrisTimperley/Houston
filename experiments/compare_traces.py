#!/usr/bin/env python3
__all__ = ['compare_traces']

from typing import Tuple, List
import argparse
import logging
import json
import os
import sys

import houston
import houston.ardu.copter
from houston.exceptions import HoustonException
from houston import Mission, MissionTrace

logger = logging.getLogger(__name__)  # type: logging.Logger
logger.setLevel(logging.DEBUG)

DESCRIPTION = """
Compares two sets of traces, generated using the same mission, to determine
whether there is a significant difference between them (i.e., does the robot
appear to behave differently?).
""".strip()


def traces_contain_same_commands(traces: List[MissionTrace]) -> bool:
    """
    Determines whether a list of traces contain the same sequence of
    command executions.
    """
    assert traces is not []

    expected = [ct.command for ct in traces[0].commands]
    for t in traces:
        actual = [ct.command for ct in t.commands]
        if actual != expected:
            return False

    return True


def compare_traces(mission: Mission,
                   traces_x: List[MissionTrace],
                   traces_y: List[MissionTrace]
                   ) -> bool:
    """
    Compares two sets of traces for a given mission and determines whether
    those sets are determined to be approximately equivalent.

    Parameters:
        mission: the mission used to generate all traces.
        traces_x: a set of traces.
        traces_y: a set of traces.

    Returns:
        True if the sets are considered approximately; False if not.
    """
    if not traces_x or not traces_y:
        raise HoustonException("cannot compare an empty set of traces.")

    print(type(traces_x[0].commands))

    # ensure that each set is homogeneous with respect to its sequence of
    # executed commands.
    is_homogeneous_x = traces_contain_same_commands(traces_x)
    is_homogeneous_y = traces_contain_same_commands(traces_y)
    if not is_homogeneous_x or not is_homogeneous_y:
        raise HoustonException("failed to compare traces: heterogeneous set of traces provided.")  # noqa: pycodestyle

    return True


def setup_logging(verbose: bool = False) -> None:
    log_to_stdout = logging.StreamHandler()
    log_to_stdout.setLevel(logging.DEBUG if verbose else logging.INFO)
    logger.addHandler(log_to_stdout)
    logging.getLogger('houston').addHandler(log_to_stdout)


def parse_args():
    p = argparse.ArgumentParser(description=DESCRIPTION)
    p.add_argument('file1', type=str, help='path to a trace file.')
    p.add_argument('file2', type=str, help='path to a trace file.')
    p.add_argument('--verbose', action='store_true',
                   help='increases logging verbosity.')
    return p.parse_args()


def load_file(fn: str) -> Tuple[Mission, List[MissionTrace]]:
    try:
        with open(fn, 'r') as f:
            jsn = json.load(f)
            mission = Mission.from_dict(jsn['mission'])
            traces = [MissionTrace.from_dict(t) for t in jsn['traces']]
        return (mission, traces)
    except FileNotFoundError:
        logger.error("failed to load trace file [%s]: file not found",
                     fn)
        raise
    except Exception:
        logger.exception("failed to load trace file [%s]", fn)
        raise


def main():
    args = parse_args()
    setup_logging(args.verbose)

    try:
        mission_x, traces_x = load_file(args.file1)
        mission_y, traces_y = load_file(args.file2)
    except Exception:
        sys.exit(1)

    if mission_x != mission_y:
        logger.error("failed to compare traces: %s",
                     "each set of traces should come from the same mission.")
        sys.exit(1)

    if compare_traces(mission_x, traces_x, traces_y):
        logger.info("traces were determined to be equivalent.")
    else:
        logger.info("traces were determined not to be equivalent.")


if __name__ == '__main__':
    main()
