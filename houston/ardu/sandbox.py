from typing import Optional
import time
import os
import sys
import threading

import dronekit
from bugzoo.client import Client as BugZooClient
from pymavlink import mavutil

from ..sandbox import Sandbox as BaseSandbox


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
        bzc = self.bugzoo.containers

        # FIXME #47
        home = "-35.362938,149.165085,584,270"
        name_bin = os.path.join(self.snapshot.source_dir,
                                "build/sitl/bin",
                                name_bin)
        speedup = self.system.configuration.speedup
        cmd = '{} --model "{}" --speedup "{}" --home "{}" --defaults "{}"'
        cmd = cmd.format(name_bin, name_model, speedup, home, fn_param)
        print("COMMAND: {}".format(cmd))

        if not verbose:
            bzc.command(self.container, cmd, block=False,
                        stdout=False, stderr=False)
            return

        execution_response = \
            bzc.command(self.container, cmd, stdout=True,
                        stderr=True, block=False)

        for line in execution_response.output:
            line = line.decode(sys.stdout.encoding).rstrip('\n')
            print(line, flush=True)

    def _start(self,
               mission: Mission,
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
        args = (binary_name, model_name, param_file, verbose)
        self.__sitl_thread = threading.Thread(target=self._launch_sitl,
                                              args=args)
        self.__sitl_thread.daemon = True
        self.__sitl_thread.start()

        # establish connection
        # TODO fix connection issue
        protocol = 'tcp'
        port = 5760
        ip = str(self.bugzoo.containers.ip_address(self.container))
        url = "{}:{}:{}".format(protocol, ip, port)
        dummy_connection = mavutil.mavlink_connection(url)
        time.sleep(10)
        dummy_connection.close()
        time.sleep(5)
        self.__connection = dronekit.connect(url, wait_ready=True)

        # wait until vehicle is ready to test
        self.__connection.wait_ready('autopilot_version')

        # wait for longitude and latitude to match their expected values, and
        # for the system to match the expected `armable` state.
        initial_lon = mission.initial_state['longitude']
        initial_lat = mission.initial_state['latitude']
        v = self.system.variable
        while True:
            observed = self.observe(0.0)
            ready_lon = v('longitude').eq(initial_lon, observed['longitude'])
            ready_lat = v('latitude').eq(initial_lat, observed['latitude'])
            ready_armable = \
                observed['armable'] == mission.initial_state['armable']
            if ready_lon and ready_lat and ready_armable:
                break
            time.sleep(0.05)

        if not self._post_connection_setup():
            print("Post connection setup failed!")

        # wait until the vehicle is in GUIDED mode
        # TODO: add timeout
        guided_mode = dronekit.VehicleMode('GUIDED')
        self.__connection.mode = guided_mode
        while self.__connection.mode != guided_mode:
            time.sleep(0.05)

    def _stop(self) -> None:
        """
        Closes any connection to a simulated vehicle inside the sandbox, before
        terminating the associated simulator.
        """
        bzc = self.bugzoo.containers

        if self.connection:
            self.connection.close()

        # close the SITL
        cmd = 'ps aux | grep -i sitl | awk {\'"\'"\'print $2\'"\'"\'} | xargs kill -2'  # noqa: pycodestyle
        bzc.command(self.container, cmd, stdout=False, stderr=False,
                    block=True)

    def _post_connection_setup(self):
        """
        Instructions to run after the connection is established.
        """
        return True
