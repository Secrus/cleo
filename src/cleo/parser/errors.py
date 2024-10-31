from __future__ import annotations

from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from cleo.parser.optparser import Option


class OptParseError(Exception):
    def __init__(self, msg: str) -> None:
        self.msg = msg

    def __str__(self) -> str:
        return self.msg


class OptionError(OptParseError):
    """
    Raised if an Option instance is created with invalid or
    inconsistent arguments.
    """

    def __init__(self, msg: str, option: Option) -> None:
        self.msg = msg
        self.option_id = str(option)

    def __str__(self) -> str:
        if self.option_id:
            return f"option {self.option_id}: {self.msg}"
        return self.msg


class OptionConflictError(OptionError):
    """
    Raised if conflicting options are added to an OptionParser.
    """


class OptionValueError(OptParseError):
    """
    Raised if an invalid option value is encountered on the command
    line.
    """


class BadOptionError(OptParseError):
    """
    Raised if an invalid option is seen on the command line.
    """

    def __init__(self, opt_str: str) -> None:
        self.opt_str = opt_str

    def __str__(self) -> str:
        return f"no such option: {self.opt_str}"


class AmbiguousOptionError(BadOptionError):
    """
    Raised if an ambiguous option is seen on the command line.
    """

    def __init__(self, opt_str: str, possibilities: list[str]) -> None:
        super().__init__(opt_str)
        self.possibilities = possibilities

    def __str__(self) -> str:
        return ("ambiguous option: {} ({}?)").format(
            self.opt_str, ", ".join(self.possibilities)
        )
