from __future__ import annotations

import textwrap

from cleo.parser.optparser import OptionParser, Option
from cleo.parser.optparser import Values


class Subcommand:
    """A subcommand of a root command-line application that may be
    invoked by a SubcommandOptionParser.
    """

    def __init__(self, name, parser=None, help="", aliases=()):
        """Creates a new subcommand. name is the primary way to invoke
        the subcommand; aliases are alternate names. parser is an
        OptionParser responsible for parsing the subcommand's options.
        help is a short description of the command. If no parser is
        given, it defaults to a new, empty OptionParser.
        """
        self.name = name
        self.parser = parser or OptionParser()
        self.aliases = aliases
        self.help = help


class SubcommandsOptionParser(OptionParser):
    """A variant of OptionParser that parses subcommands and their
    arguments.
    """

    # A singleton command used to give help on other subcommands.
    _HelpSubcommand = Subcommand(
        "help",
        OptionParser(),
        help="give detailed help on a specific sub-command",
        aliases=("?",),
    )

    def __init__(self, *args, **kwargs):
        """Create a new subcommand-aware option parser. All of the
        options to OptionParser.__init__ are supported in addition
        to subcommands, a sequence of Subcommand objects.
        """
        # The subcommand array, with the help command included.
        self.subcommands = list(kwargs.pop("subcommands", []))
        self.subcommands.append(self._HelpSubcommand)

        # A more helpful default usage.
        if "usage" not in kwargs:
            kwargs["usage"] = """
  %prog COMMAND [ARGS...]
  %prog help COMMAND"""

        # Super constructor.
        super().__init__(*args, **kwargs)

        # Adjust the help-visible name of each subcommand.
        for subcommand in self.subcommands:
            subcommand.parser.prog = f"{self.get_prog_name()} {subcommand.name}"

        # Our root parser needs to stop on the first unrecognized argument.
        self.disable_interspersed_args()

    def add_subcommand(self, cmd):
        """Adds a Subcommand object to the parser's list of commands."""
        self.subcommands.append(cmd)

    # Add the list of subcommands to the help message.
    def format_help(self, formatter=None):
        # Get the original help message, to which we will append.
        out = super().format_help(formatter)
        if formatter is None:
            formatter = self.formatter

        # Subcommands header.
        result = ["\n"]
        result.append(formatter.format_heading("Commands"))
        formatter.indent()

        # Generate the display names (including aliases).
        # Also determine the help position.
        disp_names = []
        help_position = 0
        for subcommand in self.subcommands:
            name = subcommand.name
            if subcommand.aliases:
                name += " ({})".format(", ".join(subcommand.aliases))
            disp_names.append(name)

            # Set the help position based on the max width.
            proposed_help_position = len(name) + formatter.current_indent + 2
            if proposed_help_position <= formatter.max_help_position:
                help_position = max(help_position, proposed_help_position)

                # Add each subcommand to the output.
        for subcommand, name in zip(self.subcommands, disp_names):
            # Lifted directly from optparse.py.
            name_width = help_position - formatter.current_indent - 2
            if len(name) > name_width:
                name = "%*s%s\n" % (formatter.current_indent, "", name)
                indent_first = help_position
            else:
                name = "%*s%-*s  " % (formatter.current_indent, "", name_width, name)
                indent_first = 0
            result.append(name)
            help_width = formatter.width - help_position
            help_lines = textwrap.wrap(subcommand.help, help_width)
            result.append("%*s%s\n" % (indent_first, "", help_lines[0]))
            result.extend(
                ["%*s%s\n" % (help_position, "", line) for line in help_lines[1:]]
            )
        formatter.dedent()

        # Concatenate the original help message with the subcommand
        # list.
        return out + "".join(result)

    def _subcommand_for_name(self, name):
        """Return the subcommand in self.subcommands matching the
        given name. The name may either be the name of a subcommand or
        an alias. If no subcommand matches, returns None.
        """
        for subcommand in self.subcommands:
            if name == subcommand.name or name in subcommand.aliases:
                return subcommand
        return None

    def parse_args(
        self, a=None, v=None
    ) -> tuple[Values, Subcommand, Values, list[str]]:
        """Like OptionParser.parse_args, but returns these four items:
        - options: the options passed to the root parser
        - subcommand: the Subcommand object that was invoked
        - suboptions: the options passed to the subcommand parser
        - subargs: the positional arguments passed to the subcommand
        """
        options, args = super().parse_args(a, v)

        if not args:
            # No command given.
            self.print_help()
            self.exit()
        else:
            cmdname = args.pop(0)
            subcommand = self._subcommand_for_name(cmdname)
            if not subcommand:
                self.error("unknown command " + cmdname)

        suboptions, subargs = subcommand.parser.parse_args(args)

        if subcommand is self._HelpSubcommand:
            if subargs:
                # particular
                cmdname = subargs[0]
                helpcommand = self._subcommand_for_name(cmdname)
                helpcommand.parser.print_help()
            else:
                # general
                self.print_help()
            self.exit()

        return options, subcommand, suboptions, subargs
