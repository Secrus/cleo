from __future__ import annotations

from cleo.parser.optparser import OptionParser
from cleo.parser.subcommand_parser import Subcommand
from cleo.parser.subcommand_parser import SubcommandsOptionParser


def main():
    # Some subcommands.
    add_cmd = Subcommand(
        "add",
        OptionParser(usage="%prog [OPTIONS] FILE..."),
        "add the specified files on the next commit",
    )
    add_cmd.parser.add_option(
        "-n",
        "--dry-run",
        dest="dryrun",
        help="do not perform actions, just print output",
        action="store_true",
    )

    commit_cmd = Subcommand(
        "commit",
        OptionParser(usage="%prog [OPTIONS] [FILE...]"),
        "commit the specified files or all outstanding changes",
        ("ci",),
    )

    # A few dummy subcommands for testing the help layout algorithm.
    long_cmd = Subcommand(
        "very_very_long_command_name",
        OptionParser(),
        "description should start on next line",
    )
    long_help_cmd = Subcommand(
        "somecmd",
        OptionParser(),
        "very long help text should wrap to the next line at which point "
        "the indentation should match the previous line",
        ("history",),
    )

    # Set up the global parser and its options.
    parser = SubcommandsOptionParser(
        subcommands=(add_cmd, commit_cmd, long_cmd, long_help_cmd)
    )
    parser.add_option(
        "-R",
        "--repository",
        dest="repository",
        help="repository root directory or symbolic path name",
        metavar="PATH",
    )
    parser.add_option(
        "-v", dest="verbose", help="enable additional output", action="store_true"
    )

    # Parse the global options and the subcommand options.
    options, subcommand, suboptions, subargs = parser.parse_args()

    # Here, we dispatch based on the identity of subcommand. Of course,
    # one could instead add a "func" property to all the subcommands
    # and here just call subcommand.func(suboptions, subargs) or
    # something.
    if subcommand is add_cmd:
        if subargs:
            print("Adding files:", ", ".join(subargs))
            print("Dry run:", ("yes" if suboptions.dryrun else "no"))
        else:
            # Note that calling error() on the subparser is the right
            # thing to do here. This way, the usage message reflects
            # the subcommand's usage specifically rather than just the
            # root command.
            subcommand.parser.error("need at least one file to add")
    elif subcommand is commit_cmd:
        if subargs:
            print("Committing files:", ", ".join(subargs))
        else:
            print("Committing all changes.")
    else:
        print("(dummy command)")

    # Show the global options.
    print("Repository:", (options.repository if options.repository else "(default)"))
    print("Verbose:", ("yes" if options.verbose else "no"))


if __name__ == "__main__":
    main()