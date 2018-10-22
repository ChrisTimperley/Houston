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

logger = logging.getLogger(__name__)  # type: logging.Logger
logger.setLevel(logging.DEBUG)


class NoConnectionError(BaseException):
    """
    Thrown when there is no connection to the vehicle running inside a sandbox.
    """
    def __init__(self):
        super().__init__("No connection to vehicle inside sandbox.")


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
        """
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
            raise Exception("post-connection setup failed.")  # FIXME better exception  # noqa: pycodestyle

        # wait until the vehicle is in GUIDED mode
        # TODO: add timeout
        guided_mode = dronekit.VehicleMode('GUIDED')
        self.vehicle.mode = guided_mode
        while self.vehicle.mode != guided_mode:
            time.sleep(0.05)
        logger.debug("Mode done")

    def stop(self) -> None:
        bzc = self._bugzoo.containers
        if self.connection:
            self.connection.close()
        cmd = 'ps aux | grep -i sitl | awk {\'"\'"\'print $2\'"\'"\'} | xargs kill -2'  # noqa: pycodestyle
        bzc.command(self.container, cmd, stdout=False, stderr=False,
                    block=True)

    def _on_connected(self) -> bool:
        """
        Called immediately after a connection to the vehicle is established.
        """
        return True

    def run(self, commands: Sequence[Command]) -> 'MissionOutcome':
        """
        Executes a mission, represented as a sequence of commands, and
        returns a description of the outcome.
        """
        config = self.configuration
        env = self.environment
        with self.__lock:
            outcomes = []  # type: List[CommandOutcome]
            passed = True
            # FIXME The initial command should be based on initial state
            initial = dronekit.Command(0, 0, 0,
                                       0, 16, 0, 0,
                                       0.0, 0.0, 0.0, 0.0,
                                       -35.3632607, 149.1652351, 584)
            # 10 seconds delay to allow the robot to reach its stable state
            delay = dronekit.Command(0, 0, 0,
                                     3, 93, 0, 0,
                                     10, -1, -1, -1,
                                     0, 0, 0)

            cmds = [initial]
            for cmd in commands:
                cmds.append(cmd.to_message().to_dronekit_command())
                cmds.append(delay)

            vcmds = self.vehicle.commands
            vcmds.clear()
            for cmd in cmds:
                vcmds.add(cmd)
            vcmds.upload()
            logger.debug("Mission uploaded")
            vcmds.wait_ready()

            mylock = threading.Lock()
            event = threading.Event()

            wp_state = {}
            last_wp = [-1]

            def reached(m):
                name = m.name
                message = m.message
                if name == 'MISSION_ITEM_REACHED':
                    logger.debug("**MISSION_ITEM_REACHED: %d", message.seq)
                    with mylock:
                        last_wp[0] = int(message.seq)
                        event.set()
                elif name == 'MISSION_CURRENT':
                    logger.debug("**MISSION_CURRENT: {}".format(message.seq))
                    logger.debug("STATE: {}".format(self.state))
                elif name == 'MISSION_ACK':
                    logger.debug("**MISSION_ACK: {}".format(message.type))
            self.connection.add_hooks({'reached': reached})
            self.vehicle.armed = True
            while not self.vehicle.armed:
                logger.info("waiting for the rover to be armed...")
                time.sleep(0.1)
                self.vehicle.armed = True

            self.vehicle.mode = dronekit.VehicleMode("AUTO")
            initial_state = self.state
            message = CommandLong(
                0, 0, 300, 0, 1, len(cmds) + 1, 0, 0, 0, 0, 4)
            self.connection.send(message)
            logger.debug("sent mission start message to vehicle")
            time_start = timer()

            while last_wp[0] < len(cmds) - 1:
                event.wait()
                with mylock:
                    # self.observe()
                    logger.debug("STATE: {}".format(self.state))
                    current_time = timer()
                    time_passed = current_time - time_start
                    wp_state[last_wp[0]] = (self.state, time_passed)
                    time_start = current_time
                    event.clear()

            self.connection.remove_hook('reached')
            outcomes = []
            state_before = initial_state
            mission_passed = True
            mission_time = 0.0
            for i in range(len(commands)):
                cmd_index = 1 + i * 2
                time_elapsed = wp_state[cmd_index][1]
                # FIXME this whole time elapsed thing is wrong
                state_after = wp_state[cmd_index + 1][0]
                command = commands[i]
                # determine which spec the system should observe
                spec = command.resolve(state_before, env, config)
                postcondition = spec.postcondition
                passed = postcondition.is_satisfied(command,
                                                    state_before,
                                                    state_after,
                                                    env,
                                                    config)
                mission_passed = mission_passed and passed
                outcome = CommandOutcome(command,
                                         passed,
                                         state_before,
                                         state_after,
                                         time_elapsed)
                outcomes.append(outcome)
                state_before = state_after
                mission_time += time_elapsed

            return MissionOutcome(mission_passed, outcomes, mission_time)

    def update(self, message: Message) -> None:
        logger.debug("UPDATE")
        with self.__state_lock:
            self.__state = self.__state.evolve(message,
                                               self.running_time,
                                               self.connection)
            logger.debug("S: %s", self.state)
