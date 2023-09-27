from __future__ import annotations

from cleo.exceptions import CleoValueError
from cleo.io.io import IO


class BaseComponent:
    name: str = "<unnamed_component>"

    def __init__(self, io: IO) -> None:
        self._io = io

    @property
    def io(self) -> IO:
        return self._io

    @io.setter
    def io(self, value: IO) -> None:
        if not isinstance(value, IO):
            raise CleoValueError(
                f"Cannot set object of type {type(value)} as UI component IO"
            )
        self._io = value
