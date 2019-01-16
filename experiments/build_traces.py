#!/usr/bin/env python3
"""
This script is used to record execution traces for each mission within a
provided mission suite file.
"""
from typing import List
import os
import argparse
import concurrent.futures
import json
import logging
import contextlib

import bugzoo
import bugzoo.server
import houston
from houston.exceptions import ConnectionLostError, NoConnectionError

import settings

logger = logging.getLogger('houston')  # type: logging.Logger
logger.setLevel(logging.DEBUG)

DESCRIPTION = "Builds trace files for a given set of missions."


def setup_logging(verbose: bool = False) -> None:
    log_to_stdout = logging.StreamHandler()
    log_to_stdout.setLevel(logging.DEBUG if verbose else logging.INFO)
    logging.getLogger('houston').addHandler(log_to_stdout)
    logging.getLogger('experiment').addHandler(log_to_stdout)


def parse_args():
    p = argparse.ArgumentParser(description=DESCRIPTION)
    p.add_argument('snapshot', help='the name of the BugZoo snapshot')
    p.add_argument('missions', type=str,
                   help='path to a mission files.')
    p.add_argument('output', type=str,
                   help='the directory to which the traces should be written.')
    p.add_argument('--verbose', action='store_true',
                   help='increases logging verbosity')
    p.add_argument('--repeats', type=int, default=1,
                   help='number of traces to generate for each mission.')
    p.add_argument('--threads', type=int, default=1,
                   help='number of threads to use when building trace files.')
    p.add_argument('--kill-container', action='store_true',
                   help='provision a new container for each mission.')

    return p.parse_args()


def trace(client_bugzoo: bugzoo.Client,
          container: bugzoo.Container,
          index: int,
          mission: houston.mission.Mission,
          num_repeats: int,
          dir_output: str,
          snapshot: bugzoo.Bug=None
          ) -> None:
    kill_container = (container == None)
    assert not kill_container or snapshot != None
    # generate a (very-likely-to-be) "unique" ID for the mission
    uid = hex(abs(hash(mission)))[2:][:8]
    logger.info("generating trace for mission %d: %s", index, uid)
    filename = "{}.json".format(uid)
    filename = os.path.join(dir_output, filename)
    if os.path.exists(filename):
        logger.info("skipping trace: %d ('%s' already exists)", index, filename)
        return

    try:
        traces = []  # List[MissionTrace]
        sandbox_cls = mission.system.sandbox
        if not container:
            container = client_bugzoo.containers.provision(snapshot)
            client_bugzoo.containers.prepare_for_coverage(container)
        for _ in range(num_repeats):
            with sandbox_cls.for_container(client_bugzoo,
                                           container,
                                           mission.initial_state,
                                           mission.environment,
                                           mission.configuration) as sandbox:
                t = sandbox.run_and_trace(mission.commands)
                traces.append(t)

        logger.debug("saving traces to file: %s", filename)
        with open(filename, 'w') as f:
            json.dump({'mission': mission.to_dict(),
                       'traces': [t.to_dict() for t in traces]},
                      f)
        logger.debug("saved trace to file: %s", filename)
    except (ConnectionLostError, NoConnectionError):
        logger.error("SITL crashed during trace %d: %s", index, uid)
    except (KeyboardInterrupt, SystemExit):
        raise
    except:
        logger.exception("failed to build trace %d: %s", index, uid)
    finally:
        if container and kill_container:
            del client_bugzoo.containers[container.uid]


def build_traces(client_bugzoo: bugzoo.Client,
                 snapshot: bugzoo.Bug,
                 missions: List[houston.Mission],
                 num_threads: int,
                 num_repeats: int,
                 dir_output: str,
                 kill_container: bool
                 ) -> None:
    containers = []
    futures = []
    try:
        if not kill_container:
            logger.info("preparing containers")
            for _ in range(num_threads):
                container = client_bugzoo.containers.provision(snapshot)
                client_bugzoo.containers.prepare_for_coverage(container)
                containers.append(container)
            logger.info("prepared containers")
 
            with concurrent.futures.ThreadPoolExecutor(num_threads) as e:
                for i, mission in enumerate(missions):
                    logger.debug("submitting mission %d", i)
                    container = containers[i % num_threads]
                    future = e.submit(trace, client_bugzoo, container, i, mission, num_repeats, dir_output)
                    futures.append(future)
        else:
            with concurrent.futures.ThreadPoolExecutor(num_threads) as e:
                for i, mission in enumerate(missions):
                    logger.debug("submitting mission %d", i)
                    future = e.submit(trace, client_bugzoo, None, i, mission, num_repeats, dir_output, snapshot)
                    futures.append(future)
        logger.debug("submitted all missions")
        logger.debug("waiting for missions to complete")
        concurrent.futures.wait(futures)
        logger.debug("finished executing all missions")
    finally:
        for c in containers:
            del client_bugzoo.containers[c.uid]


if __name__ == '__main__':
    args = parse_args()
    setup_logging(verbose=args.verbose)
    fn_missions = args.missions
    num_threads = args.threads
    num_repeats = args.repeats

    assert num_threads > 0
    assert num_repeats > 0

    os.makedirs(args.output, exist_ok=True)

    with open(fn_missions, 'r') as f:
        jsn = json.load(f)
    missions = [houston.Mission.from_dict(d) for d in jsn]

    # FIXME use an ephemeral server! (bugzoo.server.ephemeral())
    client_bugzoo = bugzoo.BugZoo()
    try:
        snapshot = client_bugzoo.bugs[args.snapshot]
        build_traces(client_bugzoo, snapshot, missions, num_threads, num_repeats, args.output, args.kill_container)
    finally:
        client_bugzoo.shutdown()
