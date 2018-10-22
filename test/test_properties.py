import pytest

from houston.ardu.common import ArmDisarm
from houston.ardu.copter.goto import GoTo as CopterGoTo
from houston.ardu.copter import ArduCopter


def test_command_uid():
    assert CopterGoTo.uid == 'ardu:copter:goto'
    assert ArmDisarm.uid == 'ardu:common:arm'


def test_system_name():
    assert ArduCopter.name == 'arducopter'
