import pytest

from houston.ardu.copter.goto import GoTo as CopterGoTo


def test_command_uid():
    assert CopterGoTo.uid == 'ardu:copter:goto'
