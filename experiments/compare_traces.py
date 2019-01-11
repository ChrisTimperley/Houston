#!/usr/bin/env python3
import argparse
import logging
import os
import sys

import houston

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


def main():
    args = parse_args()
    setup_logging(args.verbose)

    if not os.path.exists(args.file1):
        logger.error("trace file not found: %s", args.file1)
        sys.exit(1)
    if not os.path.exists(args.file2):
        logger.error("trace file not found: %s", args.file2)
        sys.exit(1)


if __name__ == '__main__':
    main()
