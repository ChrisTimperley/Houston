from typing import Optional, Sequence
import time
from timeit import default_timer as timer
import os
import sys
import threading
import logging

import dronekit
from bugzoo.client import Client as BugZooClient
from pymavlink import mavutil

from .connection import CommandLong, MAVLinkConnection, MAVLinkMessage
from ..sandbox import Sandbox as BaseSandbox
from ..command import Command, CommandOutcome
from ..connection import Message
from ..mission import MissionOutcome
from ..trace import MissionTrace, CommandTrace, TraceRecorder
from ..exceptions import NoConnectionError, \
    ConnectionLostError, \
    PostConnectionSetupFailed

logger = logging.getLogger(__name__)  # type: logging.Logger
logger.setLevel(logging.DEBUG)

TIME_LOST_CONNECTION = 5.0


def detect_lost_connection(f):
    """
    Decorates a given function such that any dronekit APIExceptions
    encountered during the execution of that function will be caught and thrown
    as ConnectionLostError exceptions.
    """
    def wrapped(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except dronekit.APIException:
            raise ConnectionLostError
    return wrapped


class Sandbox(BaseSandbox):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.__connection = None
        self.__sitl_thread = None

    @property
    def connection(self,
                   raise_exception: bool = True
                   ) -> Optional[dronekit.Vehicle]:
        """
        Uses dronekit to return a connection to the system running inside
        this sandbox.

        Raises:
            NoConnectionError: if there is no connection to the system running
                inside this sandbox.
        """
        if self.__connection is None and raise_exception:
            raise NoConnectionError()
        return self.__connection

    @property
    def vehicle(self,
                raise_exception: bool = True
                ) -> Optional[dronekit.Vehicle]:
        if not self.connection and raise_exception:
            raise NoConnectionError()
        return self.connection.conn

    def update(self, message: Message) -> None:
        with self.__state_lock:
            state = self.__state.evolve(message,
                                        self.running_time,
                                        self.connection)
            self.__state = state
            if self.recorder:
                self.recorder.record_state(state)
                self.recorder.record_message(message)

    def _launch_sitl(self,
                     name_bin: str = 'ardurover',
                     name_model: str = 'rover',
                     fn_param: str = '',  # FIXME what are the semantics of an empty string?  # noqa: pycodestyle
                     verbose: bool = True
                     ) -> None:
        """
        Launches the SITL inside the sandbox and blocks until its execution
        has finished.
        """
        bzc = self._bugzoo.containers

        # FIXME #47
        home = "-35.362938,149.165085,584,270"
        name_bin = os.path.join("/opt/ardupilot/build/sitl/bin",  # FIXME
                                name_bin)
        speedup = self.configuration.speedup
        cmd = '{} --model "{}" --speedup "{}" --home "{}" --defaults "{}"'
        cmd = cmd.format(name_bin, name_model, speedup, home, fn_param)
        logger.debug("launching SITL via: %s", cmd)

        if not verbose:
            bzc.command(self.container, cmd, block=False,
                        stdout=False, stderr=False)
            return

        # FIXME this will only work if we have direct access to the BugZoo
        #   daemon (i.e., this code won't work if we execute it remotely).
        execution_response = \
            bzc.command(self.container, cmd, stdout=True,
                        stderr=True, block=False)

        for line in execution_response.output:
            line = line.decode(sys.stdout.encoding).rstrip('\n')
            logger.debug(line)

    @detect_lost_connection
    def start(self,
              binary_name: str,
              model_name: str,
              param_file: str,
              verbose: bool = True
              ) -> None:
        """
        Launches the SITL inside this sandbox, and establishes a connection to
        the vehicle running inside the simulation. Blocks until SITL is
        launched and a connection is established.

        Raises:
            NoConnectionError: if a connection cannot be established.
            ConnectionLostError: if the connecton is lost before the vehicle
                is ready to receive commands.
            PostConnectionSetupFailed: if the post-connection setup phase
                failed.
        """
        # # TODO make it optional to compile with coverage (#146)
        # self._bugzoo.coverage.instrument(self.container)

        bzc = self._bugzoo.containers
        args = (binary_name, model_name, param_file, verbose)
        self.__sitl_thread = threading.Thread(target=self._launch_sitl,
                                              args=args)
        self.__sitl_thread.daemon = True
        self.__sitl_thread.start()

        # establish connection
        # TODO fix connection issue
        protocol = 'tcp'
        port = 5760
        ip = str(bzc.ip_address(self.container))
        url = "{}:{}:{}".format(protocol, ip, port)

        dummy_connection = mavutil.mavlink_connection(url)
        time.sleep(10)
        dummy_connection.close()
        time.sleep(5)
        event = threading.Event()

        def stdout(m: MAVLinkMessage):
            name = m.name
            message = m.message
            if name == "STATUSTEXT" and \
                    "EKF2 IMU0 Origin set to GPS" in str(message.text):
                logger.debug("Vehicle is ready")
                event.set()

        self.__connection = MAVLinkConnection(url, {'update': self.update,
                                                    'std': stdout})
        event.wait(10)
        self.__connection.remove_hook('std')

        # FIXME add timeout
        # wait for longitude and latitude to match their expected values, and
        # for the system to match the expected `armable` state.
        initial_lon = self.state_initial['longitude']
        initial_lat = self.state_initial['latitude']
        initial_armable = self.state_initial['armable']
        v = self.state_initial.__class__.variables
        while True:
            # self.observe()
            ready_lon = v['longitude'].eq(initial_lon, self.state['longitude'])
            ready_lat = v['latitude'].eq(initial_lat, self.state['latitude'])
            ready_armable = self.state['armable'] == initial_armable
            if ready_lon and ready_lat and ready_armable:
                break
            time.sleep(0.05)

        if not self._on_connected():
            raise PostConnectionSetupFailed

        # wait until the vehicle is in GUIDED mode
        # TODO: add timeout
        guided_mode = dronekit.VehicleMode('GUIDED')
        self.vehicle.mode = guided_mode
        while self.vehicle.mode != guided_mode:
            time.sleep(0.05)
        logger.debug("Mode done")

    def stop(self) -> None:
        logger.debug("Stopping SITL")
        bzc = self._bugzoo.containers
        if self.connection:
            self.connection.close()
        ps_cmd = 'ps aux | grep -i sitl | awk {\'"\'"\'print $2,$11\'"\'"\'}'

        out = bzc.command(self.container, ps_cmd, block=True, stdout=True)
        all_processes = out.output.splitlines()
        logger.debug("checking list of processes: %s", str(all_processes))
        for p in all_processes:
            if not p:
                continue
            pid, cmd = p.split(' ')
            if cmd.startswith('/opt/ardupilot'):
                bzc.command(self.container,
                            "kill -2 {}".format(pid),
                            block=True)
                break
        logger.debug("Killed it")
        self.__sitl_thread.join()
        logger.debug("Joined")
#       cmd = 'ps aux | grep -i sitl | awk {\'"\'"\'print $2\'"\'"\'} | xargs kill -2'  # noqa: pycodestyle
#       bzc.command(self.container, cmd, stdout=False, stderr=False,
#                   block=True)

    def _on_connected(self) -> bool:
        """
        Called immediately after a connection to the vehicle is established.
        """
        return True

    @detect_lost_connection
    def run_and_trace(self,
                      commands: Sequence[Command],
                      collect_coverage: bool = False
                      ) -> 'MissionTrace':
        """
        Executes a mission, represented as a sequence of commands, and
        returns a description of the outcome.

        Parameters:
            commands: the list of commands to be sent to the robot as
                a mission.
            collect_coverage: indicates whether or not coverage information
                should be incorporated into the trace. If True (i.e., coverage
                collection is enabled), this function expects the sandbox to be
                properly instrumented.

        Returns:
            a trace describing the execution of a sequence of commands.
        """
        config = self.configuration
        env = self.environment
        with self.__lock:
            outcomes = []  # type: List[CommandOutcome]
            passed = True
            connection_lost = threading.Event()

            # FIXME The initial command should be based on initial state
            initial = dronekit.Command(0, 0, 0,
                                       0, 16, 0, 0,
                                       0.0, 0.0, 0.0, 0.0,
                                       -35.3632607, 149.1652351, 584)
            # 10 seconds delay to allow the robot to reach its stable state
            # delay = dronekit.Command(0, 0, 0,
            #                         3, 93, 0, 0,
            #                         10, -1, -1, -1,
            #                         0, 0, 0)

            # convertin from Houston commands to dronekit commands
            cmds = [cmd.to_message().to_dronekit_command()
                    for cmd in commands]
            cmds.insert(0, initial)

            # uploading the mission to the vehicle
            vcmds = self.vehicle.commands
            vcmds.clear()
            for cmd in cmds:
                vcmds.add(cmd)
            vcmds.upload()
            logger.debug("Mission uploaded")
            vcmds.wait_ready()

            # maps each wp to the final state and time when wp was reached
            wp_to_state = {}  # Dict[int, Tuple[State, float]]
            # [wp that has last been reached, wp running at the moment]
            last_wp = [0, 0]
            # used to synchronize rw to last_wp
            wp_lock = threading.Lock()
            # is set whenever a command in mission is done
            wp_event = threading.Event()

            # NOTE dronekit connection must not use its own heartbeat checking
            def heartbeat_listener(_, __, value):
                if value > TIME_LOST_CONNECTION:
                    connection_lost.set()
                    wp_event.set()
            self.vehicle.add_attribute_listener('last_heartbeat',
                                                heartbeat_listener)

            def check_for_reached(m):
                name = m.name
                message = m.message
                if name == 'MISSION_ITEM_REACHED':
                    logger.debug("**MISSION_ITEM_REACHED: %d", message.seq)
                    if message.seq == len(cmds) - 1:
                        logger.info("Last item reached")
                        with wp_lock:
                            last_wp[1] = int(message.seq) + 1
                            wp_event.set()
                elif name == 'MISSION_CURRENT':
                    logger.debug("**MISSION_CURRENT: %d", message.seq)
                    logger.debug("STATE: {}".format(self.state))
                    if message.seq > last_wp[1]:
                        with wp_lock:
                            if message.seq > last_wp[0]:
                                last_wp[1] = message.seq
                                logger.debug("SET EVENT")
                                wp_event.set()
                elif name == 'MISSION_ACK':
                    logger.debug("**MISSION_ACK: %s", message.type)

            self.connection.add_hooks({'check_for_reached': check_for_reached})

            self.vehicle.armed = True
            while not self.vehicle.armed:
                logger.info("waiting for the rover to be armed...")
                time.sleep(0.1)
                self.vehicle.armed = True

            # starting the mission
            self.vehicle.mode = dronekit.VehicleMode("AUTO")
            initial_state = self.state
            start_message = CommandLong(
                0, 0, 300, 0, 1, len(cmds) + 1, 0, 0, 0, 0, 4)
            self.connection.send(start_message)
            logger.debug("sent mission start message to vehicle")
            time_start = timer()

            wp_to_traces = {}
            traces = []
            with self.record() as recorder:
                while last_wp[0] <= len(cmds) - 1:
                    # allow a single command to run for 5 minutes
                    logger.debug("waiting for command")
                    not_reached_timeout = wp_event.wait(300)
                    logger.debug("Event set %s", last_wp)
                    if not not_reached_timeout:
                        logger.error("Timeout occured %d", last_wp[0])
                        break
                    if connection_lost.is_set():
                        logger.error("Connection to vehicle was lost.")
                        raise ConnectionLostError
                    with wp_lock:
                        # self.observe()
                        logger.info("last_wp: %s len: %d",
                                    str(last_wp),
                                    len(cmds))
                        logger.debug("STATE: {}".format(self.state))
                        current_time = timer()
                        time_passed = current_time - time_start
                        wp_to_state[last_wp[0]] = (self.state, time_passed)
                        time_start = current_time
                        states, messages = recorder.flush()
                        cmd = commands[last_wp[0] - 1]
                        trace = CommandTrace(cmd, states)
                        wp_to_traces[last_wp[0]] = trace
                        traces.append(trace)

                        # if appropriate, store coverage files
                        if collect_coverage:
                            cm_directory = "command{}".format(last_wp[0])
                            self.__copy_coverage_files(cm_directory)

                        last_wp[0] = last_wp[1]
                        wp_event.clear()

            self.connection.remove_hook('check_for_reached')
            logger.debug("Removed hook")

            if collect_coverage:
                wp_to_state[0] = (initial_state, 0.0)
                for i in range(len(commands)):
                    command = commands[i]
                    cmd_index = 1 + i
                    if cmd_index in wp_to_traces:
                        directory = 'command{}'.format(cmd_index)
                        coverage = self.__get_coverage(directory=directory)
                        wp_to_traces[cmd_index].add_coverage(coverage)

            return MissionTrace(tuple(traces))

    def __get_coverage(self, directory: str) -> "FileLineSet":
        """
        Copies gcda files from /tmp/<directory> to /opt/ardupilot
        (where the source code is) and collects coverage results.
        """
        bzc = self._bugzoo.containers
        rm_cmd = 'cd /opt/ardupilot/ && find . -name *.gcda | xargs rm'
        cp_cmd = 'cd /tmp/{}/ardupilot && find . -name *.gcda -exec cp --parents \\{{\\}} /opt/ardupilot \\;'  # noqa: pycodestyle
        cp_cmd = cp_cmd.format(directory)

        bzc.command(self.container, rm_cmd, block=True)
        bzc.command(self.container, cp_cmd, block=True)
        coverage = bzc.read_coverage(self.container)
        # coverage = self._bugzoo.coverage.extract(self.container)
        bzc.command(self.container, rm_cmd, block=True)
        return coverage

    def __copy_coverage_files(self, directory: str) -> None:
        """
        Sends a SIGUSR1 signal to ardupilot processes running in the
        container. They will flush gcov data into gcda files that
        will be copied to /tmp/<directory> for later use.
        """
        bzc = self._bugzoo.containers
        ps_cmd = 'ps aux | grep -i sitl | awk {\'"\'"\'print $2,$11\'"\'"\'}'
        mv_cmd = 'find . -name *.gcda -exec cp --parents \\{{\\}} /tmp/{}/ \\;'
        mv_cmd = mv_cmd.format(directory)
        rm_cmd = 'find . -name *.gcda | xargs rm'

        out = bzc.command(self.container, ps_cmd, block=True, stdout=True)
        all_processes = out.output.splitlines()
        logger.debug("checking list of processes: %s", str(all_processes))
        for p in all_processes:
            if not p:
                continue
            pid, cmd = p.split(' ')
            if cmd.startswith('/opt/ardupilot'):
                bzc.command(self.container,
                            "kill -10 {}".format(pid),
                            block=True)
                break
        # coverage = self._bugzoo.coverage.extract(self.container)
        bzc.command(self.container,
                    "mkdir /tmp/{}".format(directory),
                    block=True)
        bzc.command(self.container, mv_cmd, block=True)
        bzc.command(self.container, rm_cmd, block=True)
