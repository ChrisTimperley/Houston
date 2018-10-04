from typing import Optional
import time
import os
import sys
import threading
import logging

import dronekit
from bugzoo.client import Client as BugZooClient
from pymavlink import mavutil

from ..sandbox import Sandbox as BaseSandbox

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
        self.__connection = dronekit.connect(url, wait_ready=True)

        # wait until vehicle is ready to test
        self.__connection.wait_ready('autopilot_version')

        # FIXME add timeout
        # wait for longitude and latitude to match their expected values, and
        # for the system to match the expected `armable` state.
        initial_lon = self.state_initial['longitude']
        initial_lat = self.state_initial['latitude']
        initial_armable = self.state_initial['armable']
        v = self.state_initial.__class__.variables
        while True:
            self.observe()
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
        self.__connection.mode = guided_mode
        while self.__connection.mode != guided_mode:
            time.sleep(0.05)

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
