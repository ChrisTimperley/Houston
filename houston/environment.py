__all__ = ['Environment']

from typing import Dict, Any
import json


class Environment(object):
    """
    Provides a static description of the state of the environment.
    """
    @staticmethod
    def from_file(fn: str) -> 'Environment':
        with open(fn, "r") as f:
            jsn = json.load(f)
        return Environment.from_json(jsn)

    @staticmethod
    def from_json(jsn: Dict[str, Any]) -> 'Environment':
        return Environment(jsn['constants'])

    def __init__(self, values: Dict[str, Any]) -> None:
        """
        Constructs a description of a mission environment.

        Parameters:
            values: a dictionary of environment constant values, indexed by
                the name of those constants.
        """
        self.__values = values.copy()

    def __getitem__(self, name: str):
        """
        Retrieves the value of an environmental variable with a given name.
        """
        return self.__values[name]

    def __eq__(self, other: 'Environment') -> bool:
        return self.to_json() == other.to_json()

    def __hash__(self) -> int:
        vals = tuple(self.__values.items())
        vals = sorted(vals, key=lambda x: x[0])
        return hash(tuple(vals))

    def to_json(self) -> Dict[str, Any]:
        return {'constants': self.__values.copy()}
