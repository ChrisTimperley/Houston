from typing import Type, Optional


class HoustonException(Exception):
    """
    Base class used by all of Houston's exceptions.
    """


class NoConnectionError(HoustonException):
    """
    Thrown when there is no connection to the vehicle running inside a sandbox.
    """
    def __init__(self) -> None:
        super().__init__("No connection to vehicle inside sandbox.")


class ConnectionLostError(HoustonException):
    """
    Thrown when the connection to the vehicle has been lost.
    """
    def __init__(self) -> None:
        super().__init__("Connection to vehicle has been lost.")


class PostConnectionSetupFailed(HoustonException):
    """
    Thrown when the post-connection setup phase fails.
    """
    def __init__(self, reason: Optional[str] = None) -> None:
        if reason:
            m = "An error occurred during post-connection setup: {}"
            m = m.format(reason)
        else:
            m = "An unexpected error occurred during post-connection setup."
        super().__init__(m)


class VehicleNotReadyError(PostConnectionSetupFailed):
    """
    The vehicle failed to enter a state where it was ready to accept commands
    before a timeout occurred.
    """
    def __init__(self) -> None:
        m = "timeout occurred before vehicle was ready to receive commands."
        super().__init__(m)


class NoFileSetError(HoustonException):
    """
    Thrown when writing to mission trace file has been requested, but no
    filename has been set.
    """
    def __init__(self):
        super().__init__("No file is set for the recorder.")


class InvalidExpression(HoustonException):
    """
    The s-expression does not have a valid format.
    """
    def __init__(self) -> None:
        msg = "The s-expression does not have a valid format."
        super().__init__(msg)


class UnsupportedVariableType(HoustonException):
    """
    Houston and/or Z3 do not support variables of a given Python type.
    """
    def __init__(self, type_py: Type) -> None:
        msg = "Houston and/or Z3 does not support variable type: {}"
        msg = msg.format(type_py.__name__)
        super().__init__(msg)
