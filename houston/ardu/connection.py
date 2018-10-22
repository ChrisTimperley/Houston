__all__ = ['MAVLinkMessage', 'CommandLong', 'MAVLinkConnection']


from typing import Any, List, Callable, Dict
import pymavlink
from pymavlink.mavutil import mavlink
import attr
import dronekit


from ..connection import Message, Connection


class MAVLinkGeneralMessage(Message):
    """
    Base class used by all MAVLink messages.
    """


@attr.s(frozen=True)
class CommandLong(MAVLinkGeneralMessage):
    target_system = attr.ib(type=int)
    target_component = attr.ib(type=int)
    cmd_id = attr.ib(type=int)
    confirmation = attr.ib(type=int, default=0)
    param_1 = attr.ib(type=float, default=0.0)
    param_2 = attr.ib(type=float, default=0.0)
    param_3 = attr.ib(type=float, default=0.0)
    param_4 = attr.ib(type=float, default=0.0)
    param_5 = attr.ib(type=float, default=0.0)
    param_6 = attr.ib(type=float, default=0.0)
    param_7 = attr.ib(type=float, default=0.0)

    def to_dronekit_command(self,
                            frame: int = mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT
                            ) -> dronekit.Command:
        cmd = dronekit.Command(self.target_system,
                               self.target_component,
                               0,  # Sequence number automatically saved
                               frame,
                               self.cmd_id,
                               0,  # current (not supported)
                               0,  # autocontinue (not supported)
                               self.param_1,
                               self.param_2,
                               self.param_3,
                               self.param_4,
                               self.param_5,
                               self.param_6,
                               self.param_7)
        return cmd


@attr.s(frozen=True)
class MAVLinkMessage(MAVLinkGeneralMessage):
    name = attr.ib(type=str)
    message = attr.ib(type=Any)  # FIXME MAVLink message type


HOOK_TYPE = Dict[str, Callable[[MAVLinkGeneralMessage], None]]


class MAVLinkConnection(Connection[MAVLinkGeneralMessage]):
    """
    Uses the MAVLink protocol to provide a connection to a system under test.
    """
    def __init__(self,
                 url: str,
                 hooks: HOOK_TYPE = None
                 ) -> None:
        super().__init__(hooks)
        self.__conn = dronekit.connect(url, wait_ready=True)
        self.__conn.wait_ready('autopilot_version')

        def recv(s, name: str, message):  # FIXME external types
            m = MAVLinkMessage(name, message)
            self.receive(m)
        self.__conn.add_message_listener('*', recv)

    @property
    def conn(self):
        return self.__conn

    def send(self, message: MAVLinkGeneralMessage) -> None:
        mav = self.__conn.message_factory
        if isinstance(message, CommandLong):
            mav.command_long_send(message.target_system,
                                  message.target_component,
                                  message.cmd_id,
                                  message.confirmation,
                                  message.param_1,
                                  message.param_2,
                                  message.param_3,
                                  message.param_4,
                                  message.param_5,
                                  message.param_6,
                                  message.param_7)

    def close(self):
        if self.conn:
            self.conn.close()
