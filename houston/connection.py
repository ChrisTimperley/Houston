__all__ = ['Message', 'Connection']

from typing import Generic, TypeVar, List, Callable, Dict

T = TypeVar('T')


class Message(object):
    """
    Base class used by all messages.
    """


class Connection(Generic[T]):
    """
    Provides a connection to the system under test using a given protocol.
    """
    def __init__(self, hooks: Dict[str, Callable[[T], None]]) -> None:
        """
        Establishes a new connection.

        Parameters:
            hooks: A dictionary of string (name of the hook) to callables
                that should be callednupon receiving a message via this
                connection.
        """
        self.__hooks = hooks if hooks else {}

    def receive(self, message: T) -> None:
        """
        Forwards any received messages using the hooks attached to this
        connection.
        """
        for hook in self.__hooks.values():
            hook(message)

    def send(self, message: T) -> None:
        """
        Attempts to send a given message to the system under test.
        """
        raise NotImplementedError

    def close(self) -> None:
        """
        Closes the connection if open.
        """
        raise NotImplementedError

    def add_hooks(self, hooks: Dict[str, Callable[[T], None]]) -> None:
        """
        Adds a dictionary of hooks to the set of hooks to be called
        when messages are received.
        """
        self.__hooks.update(hooks)

    def remove_hook(self, hook_name: str) -> None:
        """
        Removes a hook from hooks based on its name.
        """
        if hook_name in self.__hooks:
            self.__hooks.pop(hook_name)
