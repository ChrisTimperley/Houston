__all__ = ['MissionTrace', 'CommandTrace', 'TraceRecorder']

from typing import Tuple, Iterator, Dict, Any, Optional, Type
import attr
import json
import threading

from bugzoo.core.fileline import FileLineSet

from .command import Command
from .state import State
from .connection import Message


class TraceRecorder(object):
    def __init__(self) -> None:
        self.__lock = threading.Lock()
        self.__states = []
        self.__messages = []

    def record_message(self, message: Message) -> None:
        with self.__lock:
            self.__messages.append(message)

    def record_state(self, state: State) -> None:
        with self.__lock:
            self.__states.append(state)

    def flush(self) -> Tuple[Tuple[State, ...], Tuple[Message, ...]]:
        with self.__lock:
            states = tuple(self.__states)
            messages = tuple(self.__messages)
            self.__states = []
            self.__messages = []
        return (states, messages)


@attr.s  # (frozen=True)
class CommandTrace(object):
    command = attr.ib(type=Command)
    states = attr.ib(type=Tuple[State, ...])
    # messages = attr.ib(type=Tuple[Message, ...])
    coverage = attr.ib(type=Optional[FileLineSet], default=None)

    # TODO coverage
    # TODO messages

    @staticmethod
    def from_dict(d: Dict[str, Any],
                  system: 'Type[System]'
                  ) -> 'CommandTrace':
        command = Command.from_dict(d['command'])
        states = tuple(system.state.from_dict(s) for s in d['states'])
        if 'coverage' in d:
            coverage = FileLineSet.from_dict(d['coverage'])
        else:
            coverage = None
        return CommandTrace(command, states, coverage)

    def to_dict(self) -> Dict[str, Any]:
        cmd = {'command': self.command.to_dict(),
               'states': [s.to_dict() for s in self.states]}
        if self.coverage:
            cmd['coverage'] = self.coverage.to_dict()
        return cmd

    def add_coverage(self, coverage: FileLineSet) -> None:
        self.coverage = coverage


@attr.s  # (frozen=True)
class MissionTrace(object):
    commands = attr.ib(type=Tuple[CommandTrace, ...])

    @staticmethod
    def from_file(filename: str,
                  system: 'Type[System]'
                  ) -> 'MissionTrace':
        with open(filename, 'r') as f:
            jsn = json.load(f)
        return MissionTrace.from_dict(jsn, system)

    def to_file(self, filename: str) -> None:
        with open(filename, 'w') as f:
            json.dump(self.to_dict(), f)

    @staticmethod
    def from_dict(d: Dict[str, Any],
                  system: 'Type[System]'
                  ) -> 'MissionTrace':
        commands = tuple(CommandTrace.from_dict(c, system)
                         for c in d['commands'])
        return MissionTrace(commands)

    def to_dict(self) -> Dict[str, Any]:
        return {'commands': [c.to_dict() for c in self]}

    def __iter__(self) -> Iterator[CommandTrace]:
        """
        Returns an iterator over the traces for the sequence of commands
        performed during this mission.
        """
        yield from self.commands
