__all__ = ['Sandbox']

from ..sandbox import Sandbox as ArduSandbox


class Sandbox(ArduSandbox):
    def _start(self) -> None:
        # FIXME #66
        fn_param = '/opt/ardupilot/Tools/autotest/default_params/rover.parm'
        super().start(binary_name='ardurover',
                      model_name='rover',
                      param_file=fn_param)
