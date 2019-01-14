#!/usr/bin/env python3
__all__ = ['compare_traces']

from typing import Tuple, List
import argparse
import logging
import json
import os
import sys
import numpy as np

import houston
import houston.ardu.copter
from houston import System
from houston.exceptions import HoustonException
from houston import Mission, MissionTrace, State
from houston.state import Variable

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


def build_expected_state_distribution():
    pass


def compare_traces(mission: Mission,
                   traces_x: List[MissionTrace],
                   traces_y: List[MissionTrace],
                   tolerance_factor: float = 1.0
                   ) -> bool:
    """
    Compares two sets of traces for a given mission and determines whether
    those sets are determined to be approximately equivalent.

    Parameters:
        mission: the mission used to generate all traces.
        traces_x: a set of traces.
        traces_y: a set of traces.
        tolerance_factor: the number of standard deviations that an observed
            (continuous) variable is allowed to deviate from the mean before
            that observation is considered to be an outlier.

    Returns:
        True if the sets are considered approximately; False if not.
    """
    if not traces_x or not traces_y:
        raise HoustonException("cannot compare an empty set of traces.")

    # FIXME this shouldn't be computed on each invocation
    # determine the sets of categorical and continuous variables
    state_cls = traces_x[0].commands[0].states[0].__class__
    state_variables = list(state_cls.variables[v] for v in state_cls.variables)
    categorical_vars = set()
    continuous_vars = set()
    for var in state_variables:
        if var.typ in [int, float]:
            continuous_vars.add(var)
        else:
            categorical_vars.add(var)
    logger.debug("categorical variables: %s",
                 ', '.join([v.name for v in categorical_vars]))
    logger.debug("continuous variables: %s",
                 ', '.join([v.name for v in continuous_vars]))

    # ensure that each set is homogeneous with respect to its sequence of
    # executed commands.
    is_homogeneous_x = traces_contain_same_commands(traces_x)
    is_homogeneous_y = traces_contain_same_commands(traces_y)
    if not is_homogeneous_x or not is_homogeneous_y:
        raise HoustonException("failed to compare traces: heterogeneous set of traces provided.")  # noqa: pycodestyle

    # simplify each trace to a sequence of states, representing the state
    # of the system after the completion (or non-completion) of each command.
    def simplify_traces(traces: List[MissionTrace]
                        ) -> List[Tuple[State]]:
        return [tuple(ct.states[-1] for ct in t.commands) for t in traces]
    state_traces_x = simplify_traces(traces_x)
    state_traces_y = simplify_traces(traces_y)

    # check that values of categorical variables are consistent between traces
    # within each set
    def categorical_eq(var: Variable,
                       state_traces: List[Tuple[State]]) -> bool:
        collapse = lambda st: tuple(s[var.name] for s in st)
        expected = collapse(state_traces[0])
        return all(collapse(st) == expected for st in state_traces)

    def all_categoricals_eq(state_traces: List[Tuple[State]]) -> bool:
        return all(categorical_eq(v, state_traces) for v in categorical_vars)

    if not all_categoricals_eq(state_traces_x):
        raise HoustonException("failed to compare traces: inconsistent categorical values within X.")
    if not all_categoricals_eq(state_traces_y):
        raise HoustonException("failed to compare traces: inconsistent categorical values within Y.")

    # check if one set of traces executes more commands than the other
    if not traces_contain_same_commands([traces_x[0], traces_y[0]]):
        return False

    # build a distribution of expected values for each continuous variable at
    # the end of each command
    num_commands = len(traces_x[0].commands)
    num_traces = len(traces_x)
    for i in range(num_commands):
        for var in continuous_vars:
            vals = np.array([float(state_traces_x[j][i][var.name])
                             for j in range(num_traces)])
            mean = np.mean(vals)
            std = np.std(vals)
            tolerance = std * tolerance_factor
            logger.info("%d:%s (%.2f +/-%.2f)", i, var.name, mean, tolerance)
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
    system = System.get_by_name('arducopter')
    try:
        with open(fn, 'r') as f:
            jsn = json.load(f)
            mission = Mission.from_dict(jsn['mission'])
            traces = [MissionTrace.from_dict(t, system) for t in jsn['traces']]
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
