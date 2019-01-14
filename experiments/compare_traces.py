#!/usr/bin/env python3
__all__ = ['compare_traces']

from typing import Tuple, List, Tuple, Set
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


# FIXME precompute
def obtain_var_names(cls_state: Type[State]) -> Tuple[Set[str], Set[str]]:
    """
    Obtains the names of the categorial and continuous variables for a system.

    Parameters:
        cls_state: The class used to model the state of the system.

    Returns:
        A tuple of the form, (categorial, continuous), where each member of
        that tuple contains the set of the names of the categorial/continuous
        variables for the system.
    """
    variables = list(state_cls.variables[v] for v in state_cls.variables)
    categorical = set()  # type: Set[str]
    continuous = set()  # type: Set[str]
    for var in variables:
        if var.typ in [int, float]:
            continuous.add(var.name)
        else:
            categorical.add(var.name)
    logger.debug("categorical variables: %s", ', '.join(categorical))
    logger.debug("continuous variables: %s", ', '.join(continuous))
    return (categorial, continuous)


def matches_ground_truth(
        mission: Mission,
        candidate: MissionTrace,
        truth: List[MissionTrace],
        tolerance_factor: float = 1.0
        ) -> bool:
    """
    Determines whether a given trace, referred to as the candidate trace,
    is approximately equivalent to a set of ground truth traces for the
    same mission.

    Parameters:
        mission: the mission used to generate all traces.
        candidate: the candidate trace.
        truth: a set of ground truth traces for the provided mission, generated
            from repeat executions using an identical configuration/version of
            the SUT.
        tolerance_factor: the number of standard deviations that an observed
            (continuous) variable is allowed to deviate from the mean before
            that observation is considered to be an outlier.

    Returns:
        True if candidate trace is approximately equivalent to the ground
        truth.
    """
    if not truth:
        raise HoustonException("ground truth set must not be empty.")

    # determine the sets of categorical and continuous variables
    state_cls = candidate.commands[0].states[0].__class__
    categorial, continuous = obtain_var_names(state_cls)

    # ensure that all traces within the ground truth set execute an identical
    # sequence of commands
    if not traces_contain_same_commands(truth):
        raise HoustonException("ground truth traces have inconsistent structure")

    # simplify each trace to a sequence of states, representing the state
    # of the system after the completion (or non-completion) of each command.
    def simplify_trace(trace: MissionTrace) -> Tuple[State]:
        return tuple(ct.states[-1] for ct in t.commands)
    simple_candidate = simplify_trace(candidate)
    simple_truth = [simplify_traces(t) for t in truth]

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
    p.add_argument('candidate', type=str, help='path to a candidate trace file.')
    p.add_argument('ground-truth', type=str, help='path to a ground truth trace file.')
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
        mission_cand, traces_cand = load_file(args.candidate)
        mission_truth, traces_truth = load_file(args.ground_truth)
    except Exception:
        sys.exit(1)

    if mission_cand != mission_truth:
        logger.error("failed to compare traces: %s",
                     "all traces should come from the same mission.")
        sys.exit(1)

    if matches_ground_truth(mission_cand, traces_cand[0], traces_truth):
        logger.info("candidate trace deemed equivalent to ground truth.")
    else:
        logger.info("candidate trace deemed not equivalent to ground truth.")


if __name__ == '__main__':
    main()
