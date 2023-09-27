from __future__ import annotations

import inspect

from typing import TYPE_CHECKING
from typing import Any
from typing import ClassVar

from cleo.exceptions import CleoError
from cleo.io.inputs.definition import Definition
from cleo.io.inputs.string_input import StringInput
from cleo.io.null_io import NullIO


if TYPE_CHECKING:
    from cleo.application import Application
    from cleo.io.inputs.argument import Argument
    from cleo.io.inputs.option import Option
    from cleo.io.io import IO


class Command:
    arguments: ClassVar[list[Argument]] = []
    options: ClassVar[list[Option]] = []
    aliases: ClassVar[list[str]] = []
    usages: ClassVar[list[str]] = []
    commands: ClassVar[list[Command]] = []
    name: str | None = None

    description = ""

    help = ""

    enabled = True
    hidden = False

    def __init__(self) -> None:
        self._io: IO = None  # type: ignore[assignment]
        self._definition = Definition()
        self._full_definition: Definition | None = None
        self._application: Application | None = None
        self._ignore_validation_errors = False
        self._synopsis: dict[str, str] = {}

        self.configure()

        for i, usage in enumerate(self.usages):
            if self.name and not usage.startswith(self.name):
                self.usages[i] = f"{self.name} {usage}"

    @property
    def io(self) -> IO:
        return self._io

    def configure(self) -> None:
        for argument in self.arguments:
            self._definition.add_argument(argument)

        for option in self.options:
            self._definition.add_option(option)

    def execute(self, io: IO) -> int:
        self._io = io

        try:
            return self.handle()
        except KeyboardInterrupt:
            return 1

    def handle(self) -> int:
        """
        Execute the command.
        """
        raise NotImplementedError

    def call(self, name: str, args: str | None = None) -> int:
        """
        Call another command.
        """
        assert self.application is not None
        command = self.application.get(name)

        return self.application._run_command(
            command, self._io.with_input(StringInput(args or ""))
        )

    def call_silent(self, name: str, args: str | None = None) -> int:
        """
        Call another command silently.
        """
        assert self.application is not None
        command = self.application.get(name)

        return self.application._run_command(command, NullIO(StringInput(args or "")))

    def argument(self, name: str) -> Any:
        """
        Get the value of a command argument.
        """
        return self._io.input.argument(name)

    def option(self, name: str) -> Any:
        """
        Get the value of a command option.
        """
        return self._io.input.option(name)

    @property
    def application(self) -> Application | None:
        return self._application

    @property
    def definition(self) -> Definition:
        if self._full_definition is not None:
            return self._full_definition

        return self._definition

    @property
    def processed_help(self) -> str:
        help_text = self.help
        if not self.help:
            help_text = self.description

        is_single_command = self._application and self._application.is_single_command()

        if self._application:
            current_script = self._application.name
        else:
            current_script = inspect.stack()[-1][1]

        return help_text.format(
            command_name=self.name,
            command_full_name=current_script
            if is_single_command
            else f"{current_script} {self.name}",
            script_name=current_script,
        )

    def ignore_validation_errors(self) -> None:
        self._ignore_validation_errors = True

    def set_application(self, application: Application | None = None) -> None:
        self._application = application

        self._full_definition = None

    def interact(self, io: IO) -> None:
        """
        Interacts with the user.
        """

    def initialize(self, io: IO) -> None:
        pass

    def run(self, io: IO) -> int:
        self.merge_application_definition()

        try:
            io.input.bind(self.definition)
        except CleoError:
            if not self._ignore_validation_errors:
                raise

        self.initialize(io)

        if io.is_interactive():
            self.interact(io)

        if io.input.has_argument("command") and io.input.argument("command") is None:
            io.input.set_argument("command", self.name)

        io.input.validate()

        return self.execute(io) or 0

    def merge_application_definition(self, merge_args: bool = True) -> None:
        if self._application is None:
            return

        self._full_definition = Definition()
        self._full_definition.add_options(self._definition.options)
        self._full_definition.add_options(self._application.definition.options)

        if merge_args:
            self._full_definition.set_arguments(self._application.definition.arguments)
            self._full_definition.add_arguments(self._definition.arguments)
        else:
            self._full_definition.set_arguments(self._definition.arguments)

    def synopsis(self, short: bool = False) -> str:
        key = "short" if short else "long"

        if key not in self._synopsis:
            self._synopsis[key] = f"{self.name} {self.definition.synopsis(short)}"

        return self._synopsis[key]
