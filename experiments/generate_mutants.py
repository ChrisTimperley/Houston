"""
This script is responsible for producing a requested number of mutants for use
in a ground truth evaluation.
"""
from typing import List, Iterator, Tuple, Set, Optional
import contextlib
import logging
import json
import argparse
import random
import functools

import bugzoo
import boggart
import rooibos

logger = logging.getLogger(__name__)  # type: logging.Logger
logger.setLevel(logging.DEBUG)

MUTABLE_FILES = [
    'ArduCopter/AP_Arming.cpp',
    'ArduCopter/AP_Rally.cpp',
    'ArduCopter/AP_State.cpp',
    'ArduCopter/ArduCopter.cpp',
    'ArduCopter/Attitude.cpp',
    'ArduCopter/Copter.cpp',
    'ArduCopter/GCS_Mavlink.cpp',
    'ArduCopter/autoyaw.cpp',
    'ArduCopter/avoidance_adsb.cpp',
    'ArduCopter/baro_ground_effect.cpp',
    'ArduCopter/capabilities.cpp',
    'ArduCopter/commands.cpp',
    'ArduCopter/compassmot.cpp',
    'ArduCopter/crash_check.cpp',
    'ArduCopter/ekf_check.cpp',
    'ArduCopter/esc_calibration.cpp',
    'ArduCopter/failsafe.cpp',
    'ArduCopter/fence.cpp',
    'ArduCopter/heli.cpp',
    'ArduCopter/inertia.cpp',
#    'ArduCopter/land_detector.cpp',
    'ArduCopter/landing_gear.cpp',
    'ArduCopter/leds.cpp',
    'ArduCopter/mode.cpp',
    'ArduCopter/mode_acro.cpp',
    'ArduCopter/mode_acro_heli.cpp',
    'ArduCopter/mode_althold.cpp',
    'ArduCopter/mode_auto.cpp',
    'ArduCopter/mode_autotune.cpp',
    'ArduCopter/mode_avoid_adsb.cpp',
    'ArduCopter/mode_brake.cpp',
    'ArduCopter/mode_circle.cpp',
    'ArduCopter/mode_drift.cpp',
    'ArduCopter/mode_flip.cpp',
    'ArduCopter/mode_flowhold.cpp',
    'ArduCopter/mode_follow.cpp',
    'ArduCopter/mode_guided.cpp',
    'ArduCopter/mode_guided_nogps.cpp',
    'ArduCopter/mode_land.cpp',
    'ArduCopter/mode_loiter.cpp',
#    'ArduCopter/mode_poshold.cpp ',
    'ArduCopter/mode_rtl.cpp',
    'ArduCopter/mode_smart_rtl.cpp',
    'ArduCopter/mode_sport.cpp',
    'ArduCopter/mode_stabilize.cpp',
    'ArduCopter/mode_stabilize_heli.cpp',
    'ArduCopter/mode_throw.cpp',
#    'ArduCopter/mode_zigzag.cpp',
    'ArduCopter/motor_test.cpp',
    'ArduCopter/motors.cpp',
    'ArduCopter/navigation.cpp',
    'ArduCopter/position_vector.cpp',
    'ArduCopter/precision_landing.cpp',
    'ArduCopter/radio.cpp',
    'ArduCopter/sensors.cpp',
    'ArduCopter/setup.cpp',
    'ArduCopter/system.cpp',
    'ArduCopter/takeoff.cpp',
    'ArduCopter/terrain.cpp',
#    'ArduCopter/toy_mode.cpp',
    'ArduCopter/tuning.cpp'
]

DESCRIPTION = \
"""
Generates a specified number of acceptable mutants for the purpose of a later
ground truth evaluation.
"""

def setup_logging() -> None:
    log_to_stdout = logging.StreamHandler()
    log_to_stdout.setLevel(logging.DEBUG)
    logging.getLogger('houston').addHandler(log_to_stdout)
    logging.getLogger(__name__).addHandler(log_to_stdout)


def get_args():
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument('number', type=int,
                        help="the desired number of acceptable mutants to generate.")
    parser.add_argument('--snapshot', type=str, default='arducopter:3.6.4',
                        help='the name of the BugZoo snapshot that should be mutated.')
    parser.add_argument('--output', type=str, default='mutants.json',
                        help="the file to which the mutants should be written.")
    return parser.parse_args()


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


def all_mutations(client_bugzoo: bugzoo.Client,
                  client_boggart: boggart.Client,
                  snapshot: bugzoo.Bug
                  ) -> List[boggart.Mutation]:
    """
    Generates the set of all possible syntactic mutations to a given version of
    ArduPilot, provided as a BugZoo snapshot.
    """
    # FIXME we also need to decide which mutation operators to use.
    operators = [
        client_boggart.operators['flip-boolean-operator'],
        client_boggart.operators['flip-arithmetic-operator'],
        client_boggart.operators['flip-relational-operator']
    ]
    mutations = []
    for filename in MUTABLE_FILES:
        logger.debug("finding mutations to file [%s]", filename)
        generator = client_boggart.mutations(
            snapshot,
            filename,
            operators=operators,
            language=client_boggart.languages['C++'])
        mutations_to_file = list(generator)
        logger.debug("found %d mutations to file [%s]",
                     len(mutations_to_file), filename)
        mutations += mutations_to_file
    return mutations


def is_acceptable_mutant(client_bugzoo: bugzoo.Client,
                         client_boggart: boggart.Client,
                         snapshot: bugzoo.Bug,
                         mutation: boggart.Mutation
                         ) -> bool:
    """
    Determines whether a given mutant is suitable for use in a ground truth
    evaluation.
    """
    mutant = None  # type: Optional[boggart.Mutant]
    try:
        mutant = client_boggart.mutate(snapshot, [mutation])

        # TODO filter out program crashes

        # TODO keep semantic mutants
        return True

    except boggart.exceptions.BoggartException:
        logger.exception("failed to build mutant: %s", mutation)
        return False
    finally:
        if mutant:
            del client_boggart.mutants[mutant.uuid]


def main():
    setup_logging()
    args = get_args()
    fn_output = args.output
    num_requested = args.number
    name_snapshot = args.snapshot

    # find and shuffle the set of all candidate syntactic mutations
    with launch_servers() as (client_bugzoo, client_boggart):
        snapshot = client_bugzoo.bugs[name_snapshot]
        is_acceptable = \
            functools.partial(is_acceptable_mutant, client_bugzoo, client_boggart, snapshot)
        candidates = all_mutations(client_bugzoo, client_boggart, snapshot)
        random.shuffle(candidates)

        acceptable = []  # type: List[boggart.Mutation]
        for mutation in candidates:
            if len(acceptable) == num_requested:
                break
            if is_acceptable(mutation):
                acceptable.append(mutation)

        to_diff = lambda m: str(client_boggart.mutations_to_diff(snapshot, [m]))
        jsn = [{'mutation': m.to_dict(),
                'diff': to_diff(m)} for m in acceptable]

        with open(fn_output, 'w') as f:
            json.dump(jsn, f, indent=2)


if __name__ == '__main__':
    main()
