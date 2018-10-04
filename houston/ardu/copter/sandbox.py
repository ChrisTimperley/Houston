__all__ = ['Sandbox']

from .state import State
from ..sandbox import Sandbox as ArduSandbox


class Sandbox(ArduSandbox):
    def start(self) -> None:
        # FIXME #66
        fn_param = '/opt/ardupilot/Tools/autotest/default_params/copter.parm'
        super().start(binary_name='arducopter',
                      model_name='quad',
                      param_file=fn_param)

    def _on_connected(self) -> bool:
        if not self.connection:
            return False

        # FIXME Python 3 incompatibility in pymavlink (see #68)
        # self.connection.parameters['DISARM_DELAY'] = 0
        # self.connection.parameters['RTL_ALT'] = 0

        # wait until copter is in desired configuration
        # TODO This code doesn't work in python 3
        #   while True:
        #       if self.connection.parameters['DISARM_DELAY'] == 0 and \
        #          self.connection.parameters['RTL_ALT'] == 0:
        #           break
        #       time.sleep(0.05)
        return True
