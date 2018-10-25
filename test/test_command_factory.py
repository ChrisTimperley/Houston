import pytest

from houston.ardu.command_factory import create_command, read_commands_yml
from houston.command import Command


def test_create_command():
    c_dict = {}
    with pytest.raises(TypeError):
        assert create_command(c_dict)

    c_dict['name'] = 'TEST_COMMAND'
    with pytest.raises(TypeError):
        assert create_command(c_dict)

    c_dict['id'] = 12
    command = create_command(c_dict)
    assert issubclass(command, Command)

    c_dict['name'] = 'TEST_COMMAND2'
    c_dict['p1'] = {}
    with pytest.raises(TypeError):
        assert create_command(c_dict)
    c_dict['p1']['name'] = 'param1'
    with pytest.raises(TypeError):
        assert create_command(c_dict)
    c_dict['p1']['value'] = {}
    with pytest.raises(TypeError):
        assert create_command(c_dict)
    c_dict['p1']['value']['type'] = 'notSupported'
    with pytest.raises(Exception):
        assert create_command(c_dict)
    c_dict['p1']['value'] = {'type': 'discrete',
                             'vals': [1, 2]}
    command = create_command(c_dict)
    assert issubclass(command, Command)



