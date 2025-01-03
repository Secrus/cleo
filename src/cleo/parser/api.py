from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence, NamedTuple, Generic, TypeVar, Iterable, overload
import inspect
from types import SimpleNamespace

T = TypeVar("T")


class BadOptionError(Exception):
    pass


class HelpComposer:
    def __init__(self) -> None:
        pass


class Command:
    pass


class Option(Generic[T]):
    def __init__(
        self,
        *names: str,
        type: type[T] = str,
        default: T | list[T] | None = None,
        count: bool = False,
        flag: bool = True,
        multiple: bool = False,
        nargs: int = 1,
        hidden: bool = False,
        help: str | None = None,
        make_opts: bool = True,
        choices: Iterable[T] | None = None,
        deprecated: bool | str = False,
    ) -> None:
        self.names = names
        self.type = type
        self.default = default
        self.count = count
        self.flag = flag
        self.multiple = multiple
        self.nargs = nargs
        self.hidden = hidden
        if help:
            help = inspect.cleandoc(help)
        self.help = help
        self.make_opts = make_opts
        self.choices = choices
        if isinstance(deprecated, str):
            deprecated, deprecation_msg = True, deprecated
        else:
            deprecated, deprecation_msg = deprecated, ""
        self.deprecated = deprecated
        self.deprecation_msg = deprecation_msg
        self.short_names = []
        self.long_names = []

        # check for conflicts
        self._check_option_attrs()
        # parse option names
        self._parse_option_names()

    def _check_option_attrs(self) -> None:
        """Verify potential issues between :class:Option options."""
        pass

    def _parse_option_names(self) -> None:
        """Parse option names into short and long names."""
        pass

class Argument(Generic[T]):
    def __init__(
        self,
        name: str,
        help: str | None = None,
        required: bool = False,
        type: type[T] = str,
        multiple: bool = False,
        nargs: int = 1,
        default: T | list[T] | None = None,
        deprecated: bool | tuple[bool, str] = False,
    ) -> None:
        self.name = name
        self.required = required
        self.type = type
        self.multiple = multiple
        self.nargs = nargs
        self.default = default
        if help:
            help = inspect.cleandoc(help)
        self.help = help
        if isinstance(deprecated, tuple):
            deprecated, deprecation_msg = deprecated
        else:
            deprecated, deprecation_msg = deprecated, ""
        self.deprecated = deprecated
        self.deprecation_msg = deprecation_msg

    def _check_argument_attrs(self) -> None:
        """Verify potential issues between :class:Argument options.
        """
        pass

class Options(SimpleNamespace):
    pass


class Arguments(SimpleNamespace):
    pass


class OptionGroup(list[Option]):
    pass

class Values(SimpleNamespace):
    pass

@dataclass
class Parsed:
    options: Options
    arguments: Arguments
    remainder: list[str]

#
# class ParsingState:
#     parsed: Parsed
#     remaining: list[str]


class Parser:
    def __init__(
        self,
        app_name: str,
        help: str | None = None,
        formatter: HelpComposer | None = None,
    ) -> None:
        self.app_name = app_name
        self.help = help
        self.formatter = formatter or HelpComposer()
        self._mixed_params = True

    def add_option(self, option: Option) -> None:
        pass

    def add_argument(self, argument: Argument) -> None:
        pass

    @overload
    def parse_args(self, args: Sequence[str] | None = None) -> Values:
        ...

    def parse_args(self, args: Sequence[str] | None = None, model: T | None = None) -> T:
        if not args:
            import sys
            args = sys.argv[1:]

        args = args[:]
        found_args = []
        remaining_args = args

        while remaining_args:
            arg = remaining_args.pop(0)

            if arg == "--":
                # all remaining args are treated as "unparsed"
                remaining_args = remaining_args[1:]
                break
            elif arg[0:2] == "--" and len(arg) > 2:
                # parse options like --long-opt
                self._parse_long_opt(arg, remaining_args)
            elif arg[:1] == "-" and len(arg) > 1:
                # parse options like -s
                self._parse_short_opt(arg, remaining_args)
            else:
                # arguments not claimed as option values
                found_args.append(arg)


        return Parsed(Options(**{}), Arguments(**{}), remaining_args)

    def _parse_long_opt(self, arg: str, rargs: list[str]) -> None:
        # REMEMBER: make parsing `--abc`/`--no-abc` possible for boolean
        pass

    def _parse_short_opt(self, arg: str, rargs: list[str]) -> None:
        pass



