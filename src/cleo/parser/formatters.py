from __future__ import annotations

from abc import abstractmethod
import textwrap
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cleo.parser.optparser import OptionParser, Option, NO_DEFAULT

class HelpFormatter:
    """
    Abstract base class for formatting option help.  OptionParser
    instances should use one of the HelpFormatter subclasses for
    formatting help; by default IndentedHelpFormatter is used.

    Instance attributes:
      parser : OptionParser
        the controlling OptionParser instance
      indent_increment : int
        the number of columns to indent per nesting level
      max_help_position : int
        the maximum starting column for option help text
      help_position : int
        the calculated starting column for option help text;
        initially the same as the maximum
      width : int
        total number of columns for output (pass None to constructor for
        this value to be taken from the $COLUMNS environment variable)
      level : int
        current indentation level
      current_indent : int
        current indentation level (in columns)
      help_width : int
        number of columns available for option help text (calculated)
      default_tag : str
        text to replace with each option's default value, "%default"
        by default.  Set to false value to disable default value expansion.
      option_strings : { Option : str }
        maps Option instances to the snippet of help text explaining
        the syntax of that option, e.g. "-h, --help" or
        "-fFILE, --file=FILE"
      _short_opt_fmt : str
        format string controlling how short options with values are
        printed in help text.  Must be either "%s%s" ("-fFILE") or
        "%s %s" ("-f FILE"), because those are the two syntaxes that
        Optik supports.
      _long_opt_fmt : str
        similar but for long options; must be either "%s %s" ("--file FILE")
        or "%s=%s" ("--file=FILE").
    """

    NO_DEFAULT_VALUE: str = "none"

    def __init__(
        self,
        indent_increment: int,
        max_help_position: int,
        short_first: int,
        width: int | None = None,
    ) -> None:
        self.parser: OptionParser = None
        self.indent_increment: int = indent_increment
        # TODO: proper detection

        # if width is None:
        #     try:
        #         width = int(os.environ["COLUMNS"])
        #     except (KeyError, ValueError):
        #         width = 80
        #     width -= 2
        self.width: int = 180 #width
        _pos = min(max_help_position, max(width - 20, indent_increment * 2))
        self.help_position: int = _pos
        self.max_help_position: int = _pos
        self.current_indent: int = 0
        self.level: int = 0
        self.help_width: int = None  # computed later
        self.short_first = short_first
        self.default_tag: str = "%default"
        self.option_strings: dict[Option, str] = {}
        self._short_opt_fmt: str = "%s %s"
        self._long_opt_fmt: str = "%s=%s"

    def set_parser(self, parser: OptionParser) -> None:
        self.parser = parser

    def set_short_opt_delimiter(self, delim: str) -> None:
        if delim not in ("", " "):
            raise ValueError(f"invalid metavar delimiter for short options: {delim!r}")
        self._short_opt_fmt = "%s" + delim + "%s"

    def set_long_opt_delimiter(self, delim: str) -> None:
        if delim not in ("=", " "):
            raise ValueError(f"invalid metavar delimiter for long options: {delim!r}")
        self._long_opt_fmt = "%s" + delim + "%s"

    def indent(self) -> None:
        self.current_indent += self.indent_increment
        self.level += 1

    def dedent(self) -> None:
        self.current_indent -= self.indent_increment
        assert self.current_indent >= 0, "Indent decreased below 0."
        self.level -= 1

    @abstractmethod
    def format_usage(self, usage):
        raise NotImplementedError("subclasses must implement")

    @abstractmethod
    def format_heading(self, heading):
        raise NotImplementedError("subclasses must implement")

    def _format_text(self, text):
        """
        Format a paragraph of free-form text for inclusion in the
        help output at the current indentation level.
        """
        text_width = max(self.width - self.current_indent, 11)
        indent = " " * self.current_indent
        return textwrap.fill(
            text, text_width, initial_indent=indent, subsequent_indent=indent
        )

    def format_description(self, description: str | None = None) -> str:
        if description:
            return self._format_text(description) + "\n"
        return ""

    def format_epilog(self, epilog: str | None = None) -> str:
        if epilog:
            return "\n" + self._format_text(epilog) + "\n"
        return ""

    def expand_default(self, option: Option) -> str:
        if self.parser is None or not self.default_tag:
            return option.help

        default_value = self.parser.defaults.get(option.dest)
        if default_value is NO_DEFAULT or default_value is None:
            default_value = self.NO_DEFAULT_VALUE

        return option.help.replace(self.default_tag, str(default_value))

    def format_option(self, option: Option) -> str:
        # The help for each option consists of two parts:
        #   * the opt strings and metavars
        #     eg. ("-x", or "-fFILENAME, --file=FILENAME")
        #   * the user-supplied help string
        #     eg. ("turn on expert mode", "read data from FILENAME")
        #
        # If possible, we write both of these on the same line:
        #   -x      turn on expert mode
        #
        # But if the opt string list is too long, we put the help
        # string on a second line, indented to the same column it would
        # start in if it fit on the first line.
        #   -fFILENAME, --file=FILENAME
        #           read data from FILENAME
        result = []
        opts = self.option_strings[option]
        opt_width = self.help_position - self.current_indent - 2
        if len(opts) > opt_width:
            opts = "%*s%s\n" % (self.current_indent, "", opts)
            indent_first = self.help_position
        else:  # start help on same line as opts
            opts = "%*s%-*s  " % (self.current_indent, "", opt_width, opts)
            indent_first = 0
        result.append(opts)
        if option.help:
            help_text = self.expand_default(option)
            help_lines = textwrap.wrap(help_text, self.help_width)
            result.append("%*s%s\n" % (indent_first, "", help_lines[0]))
            result.extend(
                ["%*s%s\n" % (self.help_position, "", line) for line in help_lines[1:]]
            )
        elif opts[-1] != "\n":
            result.append("\n")
        return "".join(result)

    def store_option_strings(self, parser: OptionParser) -> None:
        self.indent()
        max_len = 0
        for opt in parser.option_list:
            strings = self.format_option_strings(opt)
            self.option_strings[opt] = strings
            max_len = max(max_len, len(strings) + self.current_indent)
        self.indent()
        for group in parser.option_groups:
            for opt in group.option_list:
                strings = self.format_option_strings(opt)
                self.option_strings[opt] = strings
                max_len = max(max_len, len(strings) + self.current_indent)
        self.dedent()
        self.dedent()
        self.help_position = min(max_len + 2, self.max_help_position)
        self.help_width = max(self.width - self.help_position, 11)

    def format_option_strings(self, option: Option) -> str:
        """Return a comma-separated list of option strings & metavariables."""
        if option.takes_value():
            metavar = option.metavar or option.dest.upper()
            short_opts = [
                self._short_opt_fmt % (sopt, metavar) for sopt in option._short_opts
            ]
            long_opts = [
                self._long_opt_fmt % (lopt, metavar) for lopt in option._long_opts
            ]
        else:
            short_opts = option._short_opts
            long_opts = option._long_opts

        opts = short_opts + long_opts if self.short_first else long_opts + short_opts

        return ", ".join(opts)


class IndentedHelpFormatter(HelpFormatter):
    """Format help with indented section bodies."""

    def __init__(
        self,
        indent_increment: int = 2,
        max_help_position: int = 24,
        width: int | None = None,
        short_first: int = 1,
    ) -> None:
        super().__init__(indent_increment, max_help_position, width, short_first)

    def format_usage(self, usage: str) -> str:
        return "Usage: %s\n" % usage

    def format_heading(self, heading: str) -> str:
        return "%*s%s:\n" % (self.current_indent, "", heading)


class TitledHelpFormatter(HelpFormatter):
    """Format help with underlined section headers."""

    def __init__(
        self,
        indent_increment: int = 0,
        max_help_position: int = 24,
        width: int | None = None,
        short_first: int = 0,
    ) -> None:
        super().__init__(indent_increment, max_help_position, width, short_first)

    def format_usage(self, usage: str) -> str:
        return "{}  {}\n".format(self.format_heading("Usage"), usage)

    def format_heading(self, heading: str) -> str:
        return "{}\n{}\n".format(heading, "=-"[self.level] * len(heading))

