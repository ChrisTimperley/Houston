#!/usr/bin/env python3
from typing import Tuple
import argparse
import logging
import json
import os
import sys

import houston
from houston import Mission, MissionTrace

logger = logging.getLogger(__name__)  # type: logging.Logger
logger.setLevel(logging.DEBUG)

DESCRIPTION = """
Compares two sets of traces, generated using the same mission, to determine
whether there is a significant difference between them (i.e., does the robot
appear to behave differently?).
""".strip()


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


def load_file(fn: str) -> Tuple[Mission, MissionTrace]:
    try:
        with open(fn, 'r') as f:
            jsn = json.load(f)
            mission = Mission.from_dict(jsn['mission'])
            traces = [MissionTrace(t) for t in jsn['traces']]
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


if __name__ == '__main__':
    main()
