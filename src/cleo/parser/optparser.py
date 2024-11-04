from __future__ import annotations

from abc import ABC
import os
import sys

from typing import IO, TYPE_CHECKING, Iterable
from typing import Any
from typing import Callable
from typing import Literal
from typing import NoReturn

from cleo.parser.errors import AmbiguousOptionError
from cleo.parser.errors import BadOptionError
from cleo.parser.errors import OptionConflictError
from cleo.parser.errors import OptionError
from cleo.parser.errors import OptionValueError
from cleo.parser.formatters import IndentedHelpFormatter, TitledHelpFormatter

if TYPE_CHECKING:
    from cleo.parser.formatters import HelpFormatter


def _repr(self):
    return f"<{self.__class__.__name__} at 0x{id(self):x}: {self}>"


def _parse_num(val, type_):
    if val[:2].lower() == "0x":  # hexadecimal
        radix = 16
    elif val[:2].lower() == "0b":  # binary
        radix = 2
        val = val[2:] or "0"  # have to remove "0b" prefix
    elif val[:1] == "0":  # octal
        radix = 8
    else:  # decimal
        radix = 10

    return type_(val, radix)


def _parse_int(val):
    return _parse_num(val, int)


_builtin_cvt = {
    "int": (_parse_int, "integer"),
    "long": (_parse_int, "integer"),
    "float": (float, "floating-point"),
    "complex": (complex, "complex"),
}


def check_builtin(option: Option, opt: Any, value: str) -> Any:
    (cvt, what) = _builtin_cvt[option.type]
    try:
        return cvt(value)
    except ValueError:
        raise OptionValueError(f"option {opt}: invalid {what} value: {value!r}")


def check_choice(option: Option, opt: Any, value: str) -> str:
    if value in option.choices:
        return value
    choices = ", ".join(map(repr, option.choices))
    raise OptionValueError(
        f"option {opt}: invalid choice: {value!r} (choose from {choices})"
    )


# Not supplying a default is different from a default of None,
# so we need an explicit "not supplied" value.
NO_DEFAULT: tuple[str, ...] = ("NO", "DEFAULT")

SUPPRESS_HELP: str = "SUPPRESS"+"HELP"
SUPPRESS_USAGE: str = "SUPPRESS"+"USAGE"


class Option:
    """
    Instance attributes:
      _short_opts : [string]
      _long_opts : [string]

      action : string
      type : string
      dest : string
      default : any
      nargs : int
      const : any
      choices : [string]
      callback : function
      callback_args : (any*)
      callback_kwargs : { string : any }
      help : string
      metavar : string
    """

    # The list of instance attributes that may be set through
    # keyword args to the constructor.
    ATTRS: list[str] = [
        "action",
        "type",
        "dest",
        "default",
        "nargs",
        "const",
        "choices",
        "callback",
        "callback_args",
        "callback_kwargs",
        "help",
        "metavar",
    ]

    # The set of actions allowed by option parsers.  Explicitly listed
    # here so the constructor can validate its arguments.
    ACTIONS: tuple[str, ...] = (
        "store",
        "store_const",
        "store_true",
        "store_false",
        "append",
        "append_const",
        "count",
        "callback",
        "help",
        "version",
    )

    # The set of actions that involve storing a value somewhere;
    # also listed just for constructor argument validation.  (If
    # the action is one of these, there must be a destination.)
    STORE_ACTIONS: tuple[str, ...] = (
        "store",
        "store_const",
        "store_true",
        "store_false",
        "append",
        "append_const",
        "count",
    )

    # The set of actions for which it makes sense to supply a value
    # type, ie. which may consume an argument from the command line.
    TYPED_ACTIONS: tuple[str, ...] = ("store", "append", "callback")

    # The set of actions which *require* a value type, ie. that
    # always consume an argument from the command line.
    ALWAYS_TYPED_ACTIONS: tuple[str, ...] = ("store", "append")

    # The set of actions which take a 'const' attribute.
    CONST_ACTIONS: tuple[str, ...] = ("store_const", "append_const")

    # The set of known types for option parsers.  Again, listed here for
    # constructor argument validation.
    TYPES: tuple[str, ...] = ("string", "int", "long", "float", "complex", "choice")

    # Dictionary of argument checking functions, which convert and
    # validate option arguments according to the option type.
    #
    # Signature of checking functions is:
    #   check(option : Option, opt : string, value : string) -> any
    # where
    #   option is the Option instance calling the checker
    #   opt is the actual option seen on the command-line
    #     (eg. "-a", "--file")
    #   value is the option argument seen on the command-line
    #
    # The return value should be in the appropriate Python type
    # for option.type -- eg. an integer if option.type == "int".
    #
    # If no checker is defined for a type, arguments will be
    # unchecked and remain strings.
    TYPE_CHECKER: dict[str, Callable[[Option, str, Any], Any]] = {
        "int": check_builtin,
        "long": check_builtin,
        "float": check_builtin,
        "complex": check_builtin,
        "choice": check_choice,
    }

    # CHECK_METHODS is a list of unbound method objects; they are called
    # by the constructor, in order, after all attributes are
    # initialized.  The list is created and filled in later, after all
    # the methods are actually defined.  (I just put it here because I
    # like to define and document all class attributes in the same
    # place.)  Subclasses that add another _check_*() method should
    # define their own CHECK_METHODS list that adds their check method
    # to those from this class.
    CHECK_METHODS: list[Callable[..., Any]] | None #= None

    # -- Constructor/initialization methods ----------------------------
    action: str
    dest: str | None
    default: Any
    nargs: int
    type: Any
    callback: Callable[..., Any] | None
    callback_args: tuple[Any, ...] | None
    callback_kwargs: dict[str, Any] | None
    help: str | None
    metavar: str | None
    choices: Iterable[str]

    def __init__(self, *opts: str | None, **attrs):
        # Set _short_opts, _long_opts attrs from 'opts' tuple.
        # Have to be set now, in case no option strings are supplied.
        self._short_opts: list[str] = []
        self._long_opts: list[str] = []
        opts = self._check_opt_strings(opts)
        self._set_opt_strings(opts)

        # Set all other attrs (action, type, etc.) from 'attrs' dict
        for attr in self.ATTRS:
            if attr in attrs:
                setattr(self, attr, attrs[attr])
                del attrs[attr]
            else:
                if attr == "default":
                    setattr(self, attr, NO_DEFAULT)
                else:
                    setattr(self, attr, None)
        if attrs:
            attrs = sorted(attrs.keys())
            raise OptionError(
                f"invalid keyword arguments: {', '.join(attrs)}", self
            )

        # Check all the attributes we just set.  There are lots of
        # complicated interdependencies, but luckily they can be farmed
        # out to the _check_*() methods listed in CHECK_METHODS -- which
        # could be handy for subclasses!  The one thing these all share
        # is that they raise OptionError if they discover a problem.
        for checker in self.CHECK_METHODS:
            checker(self)

    def _check_opt_strings(self, opts: Iterable[str | None]) -> list[str]:
        # Filter out None because early versions of Optik had exactly
        # one short option and one long option, either of which
        # could be None.
        opts = [opt for opt in opts if opt]
        if not opts:
            raise TypeError("at least one option string must be supplied")
        return opts

    def _set_opt_strings(self, opts: list[str]) -> None:
        for opt in opts:
            if len(opt) < 2:
                raise OptionError(
                    f"invalid option string {opt!r}: "
                    "must be at least two characters long",
                    self,
                )
            if len(opt) == 2:
                if not (opt[0] == "-" and opt[1] != "-"):
                    raise OptionError(
                        f"invalid short option string {opt!r}: "
                        "must be of the form -x, (x any non-dash char)",
                        self,
                    )
                self._short_opts.append(opt)
            else:
                if not (opt[0:2] == "--" and opt[2] != "-"):
                    raise OptionError(
                        f"invalid long option string {opt!r}: "
                        "must start with --, followed by non-dash",
                        self,
                    )
                self._long_opts.append(opt)

    def _check_action(self) -> None:
        if self.action is None:
            self.action = "store"
        elif self.action not in self.ACTIONS:
            raise OptionError(f"invalid action: {self.action!r}", self)

    def _check_type(self) -> None:
        if self.type is None:
            if self.action in self.ALWAYS_TYPED_ACTIONS:
                if self.choices is not None:
                    # The "choices" attribute implies "choice" type.
                    self.type = "choice"
                else:
                    # No type given?  "string" is the most sensible default.
                    self.type = "string"
        else:
            # Allow type objects or builtin type conversion functions
            # (int, str, etc.) as an alternative to their names.
            if isinstance(self.type, type):
                self.type = self.type.__name__

            if self.type == "str":
                self.type = "string"

            if self.type not in self.TYPES:
                raise OptionError(f"invalid option type: {self.type!r}", self)
            if self.action not in self.TYPED_ACTIONS:
                raise OptionError(
                    f"must not supply a type for action {self.action!r}", self
                )

    def _check_choice(self) -> None:
        if self.type == "choice":
            if self.choices is None:
                raise OptionError(
                    "must supply a list of choices for type 'choice'", self
                )
            if not isinstance(self.choices, (tuple, list)):
                raise OptionError(
                    "choices must be a list of strings ('{}' supplied)".format(
                        str(type(self.choices)).split("'")[1]
                    ),
                    self,
                )
        elif self.choices is not None:
            raise OptionError(f"must not supply choices for type {self.type!r}", self)

    def _check_dest(self) -> None:
        # No destination given, and we need one for this action.  The
        # self.type check is for callbacks that take a value.
        takes_value = self.action in self.STORE_ACTIONS or self.type is not None
        if self.dest is None and takes_value:
            # Glean a destination from the first long option string,
            # or from the first short option string if no long options.
            if self._long_opts:
                # eg. "--foo-bar" -> "foo_bar"
                self.dest = self._long_opts[0][2:].replace("-", "_")
            else:
                self.dest = self._short_opts[0][1]

    def _check_const(self) -> None:
        if self.action not in self.CONST_ACTIONS and self.const is not None:
            raise OptionError(
                f"'const' must not be supplied for action {self.action!r}", self
            )

    def _check_nargs(self) -> None:
        if self.action in self.TYPED_ACTIONS:
            if self.nargs is None:
                self.nargs = 1
        elif self.nargs is not None:
            raise OptionError(
                f"'nargs' must not be supplied for action {self.action!r}", self
            )

    def _check_callback(self) -> None:
        if self.action == "callback":
            if not callable(self.callback):
                raise OptionError(f"callback not callable: {self.callback!r}", self)
            if self.callback_args is not None and not isinstance(
                self.callback_args, tuple
            ):
                raise OptionError(
                    f"callback_args, if supplied, must be a tuple: not {self.callback_args!r}",
                    self,
                )
            if self.callback_kwargs is not None and not isinstance(
                self.callback_kwargs, dict
            ):
                raise OptionError(
                    f"callback_kwargs, if supplied, must be a dict: not {self.callback_kwargs!r}",
                    self,
                )
        else:
            if self.callback is not None:
                raise OptionError(
                    f"callback supplied ({self.callback!r}) for non-callback option",
                    self,
                )
            if self.callback_args is not None:
                raise OptionError(
                    "callback_args supplied for non-callback option", self
                )
            if self.callback_kwargs is not None:
                raise OptionError(
                    "callback_kwargs supplied for non-callback option", self
                )

    CHECK_METHODS = [_check_action,
                     _check_type,
                     _check_choice,
                     _check_dest,
                     _check_const,
                     _check_nargs,
                     _check_callback]
    # -- Miscellaneous methods -----------------------------------------

    def __str__(self) -> str:
        return "/".join(self._short_opts + self._long_opts)

    __repr__ = _repr

    def takes_value(self) -> bool:
        return self.type is not None

    def get_opt_string(self) -> str:
        if self._long_opts:
            return self._long_opts[0]
        return self._short_opts[0]

    # -- Processing methods --------------------------------------------

    def check_value(self, opt: str, value: Any) -> Any:
        checker = self.TYPE_CHECKER.get(self.type)
        if checker is None:
            return value
        return checker(self, opt, value)

    def convert_value(self, opt: str, value: Any) -> Any:
        if value is not None:
            if self.nargs == 1:
                return self.check_value(opt, value)
            return tuple([self.check_value(opt, v) for v in value])
        return None

    def process(self, opt: Any, value: Any, values: Any, parser: OptionParser) -> int:
        # First, convert the value(s) to the right type.  Howl if any
        # value(s) are bogus.
        value = self.convert_value(opt, value)

        # And then take whatever action is expected of us.
        # This is a separate method to make life easier for
        # subclasses to add new actions.
        return self.take_action(self.action, self.dest, opt, value, values, parser)

    def take_action(
        self,
        action: str,
        dest: str,
        opt: Any,
        value: Any,
        values: Any,
        parser: OptionParser,
    ) -> int:
        if action == "store":
            setattr(values, dest, value)
        elif action == "store_const":
            setattr(values, dest, self.const)
        elif action == "store_true":
            setattr(values, dest, True)
        elif action == "store_false":
            setattr(values, dest, False)
        elif action == "append":
            values.ensure_value(dest, []).append(value)
        elif action == "append_const":
            values.ensure_value(dest, []).append(self.const)
        elif action == "count":
            setattr(values, dest, values.ensure_value(dest, 0) + 1)
        elif action == "callback":
            args = self.callback_args or ()
            kwargs = self.callback_kwargs or {}
            self.callback(self, opt, value, parser, *args, **kwargs)
        elif action == "help":
            parser.print_help()
            parser.exit()
        elif action == "version":
            parser.print_version()
            parser.exit()
        else:
            raise ValueError(f"unknown action {self.action!r}")

        return 1




class Values:
    def __init__(self, defaults: dict[str, Any] | None = None) -> None:
        if defaults:
            for attr, val in defaults.items():
                setattr(self, attr, val)

    def __str__(self) -> str:
        return str(self.__dict__)

    __repr__ = _repr

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Values):
            return self.__dict__ == other.__dict__
        if isinstance(other, dict):
            return self.__dict__ == other
        return NotImplemented

    def _update_careful(self, dict_: dict[str, Any]) -> None:
        """
        Update the option values from an arbitrary dictionary, but only
        use keys from dict that already have a corresponding attribute
        in self.  Any keys in dict without a corresponding attribute
        are silently ignored.
        """
        for attr in dir(self):
            if attr in dict_:
                dval = dict_[attr]
                if dval is not None:
                    setattr(self, attr, dval)

    def _update_loose(self, dict_: dict[str, Any]) -> None:
        """
        Update the option values from an arbitrary dictionary,
        using all keys from the dictionary regardless of whether
        they have a corresponding attribute in self or not.
        """
        self.__dict__.update(dict_)

    def _update(self, dict_: dict[str, Any], mode: Literal["careful", "loose"]) -> None:
        if mode == "careful":
            self._update_careful(dict_)
        elif mode == "loose":
            self._update_loose(dict_)
        else:
            raise ValueError(f"invalid update mode: {mode!r}")

    def read_module(self, modname: str, mode: str = "careful") -> None:
        __import__(modname)
        mod = sys.modules[modname]
        self._update(vars(mod), mode)

    def read_file(self, filename: str, mode: str = "careful") -> None:
        vars_ = {}
        exec(open(filename).read(), vars_)
        self._update(vars_, mode)

    def ensure_value(self, attr: str, value: Any) -> Any:
        if not hasattr(self, attr) or getattr(self, attr) is None:
            setattr(self, attr, value)
        return getattr(self, attr)


class OptionContainer(ABC):
    """
    Abstract base class.

    Class attributes:
      standard_option_list : [Option]
        list of standard options that will be accepted by all instances
        of this parser class (intended to be overridden by subclasses).

    Instance attributes:
      option_list : [Option]
        the list of Option objects contained by this OptionContainer
      _short_opt : { string : Option }
        dictionary mapping short option strings, eg. "-f" or "-X",
        to the Option instances that implement them.  If an Option
        has multiple short option strings, it will appear in this
        dictionary multiple times. [1]
      _long_opt : { string : Option }
        dictionary mapping long option strings, eg. "--file" or
        "--exclude", to the Option instances that implement them.
        Again, a given Option can occur multiple times in this
        dictionary. [1]
      defaults : { string : any }
        dictionary mapping option destination names to default
        values for each destination [1]

    [1] These mappings are common to (shared by) all components of the
        controlling OptionParser, where they are initially created.

    """

    def __init__(
        self,
        option_class: type[Option],
        conflict_handler: Literal["error", "resolve"],
        description: str | None,
    ) -> None:
        # Initialize the option list and related data structures.
        # This method must be provided by subclasses, and it must
        # initialize at least the following instance attributes:
        # option_list, _short_opt, _long_opt, defaults.
        self._create_option_list()

        self.option_class: type[Option] = option_class
        self.set_conflict_handler(conflict_handler)
        self.set_description(description)

    def _create_option_mappings(self):
        # For use by OptionParser constructor -- create the main
        # option mappings used by this OptionParser and all
        # OptionGroups that it owns.
        self._short_opt: dict[str, Option] = {}  # single letter -> Option instance
        self._long_opt: dict[str, Option] = {}  # long option -> Option instance
        self.defaults: dict[str, Any] = {}  # maps option dest -> default value

    def _share_option_mappings(self, parser: OptionParser) -> None:
        # For use by OptionGroup constructor -- use shared option
        # mappings from the OptionParser that owns this OptionGroup.
        self._short_opt = parser._short_opt
        self._long_opt = parser._long_opt
        self.defaults = parser.defaults

    def set_conflict_handler(self, handler: Literal["error", "resolve"]) -> None:
        if handler not in ("error", "resolve"):
            raise ValueError(f"invalid conflict_resolution value {handler!r}")
        self.conflict_handler = handler

    def set_description(self, description: str | None) -> None:
        self.description = description

    def get_description(self) -> str | None:
        # TODO: property
        return self.description

    def destroy(self) -> None:
        """see OptionParser.destroy()."""
        del self._short_opt
        del self._long_opt
        del self.defaults

    # -- Option-adding methods -----------------------------------------

    def _check_conflict(self, option: Option) -> None:
        conflict_opts = []
        for opt in option._short_opts:
            if opt in self._short_opt:
                conflict_opts.append((opt, self._short_opt[opt]))
        for opt in option._long_opts:
            if opt in self._long_opt:
                conflict_opts.append((opt, self._long_opt[opt]))

        if conflict_opts:
            handler = self.conflict_handler
            if handler == "error":
                raise OptionConflictError(
                    "conflicting option string(s): {}".format(
                        ", ".join([co[0] for co in conflict_opts])
                    ),
                    option,
                )
            if handler == "resolve":
                for opt, c_option in conflict_opts:
                    if opt.startswith("--"):
                        c_option._long_opts.remove(opt)
                        del self._long_opt[opt]
                    else:
                        c_option._short_opts.remove(opt)
                        del self._short_opt[opt]
                    if not (c_option._short_opts or c_option._long_opts):
                        c_option.container.option_list.remove(c_option)

    # @overload
    # def add_option(self, opt: Option, /) -> Option:
    #     ...
    #
    # @overload
    # def add_option(self, arg: str, /, *args: str | None, **kwargs) -> Option:
    #     ...
    # TODO: figure out typing
    def add_option(self, *args, **kwargs) -> Option:
        """add_option(Option)
        add_option(opt_str, ..., kwarg=val, ...)
        """
        if isinstance(args[0], str):
            option = self.option_class(*args, **kwargs)
        elif len(args) == 1 and not kwargs:
            option = args[0]
            if not isinstance(option, Option):
                raise TypeError(f"not an Option instance: {option!r}")
        else:
            raise TypeError("invalid arguments")

        self._check_conflict(option)

        self.option_list.append(option)
        option.container = self
        for opt in option._short_opts:
            self._short_opt[opt] = option
        for opt in option._long_opts:
            self._long_opt[opt] = option

        if option.dest is not None:  # option has a dest, we need a default
            if option.default is not NO_DEFAULT:
                self.defaults[option.dest] = option.default
            elif option.dest not in self.defaults:
                self.defaults[option.dest] = None

        return option

    def add_options(self, option_list: list[Option]) -> None:
        for option in option_list:
            self.add_option(option)

    # -- Option query/removal methods ----------------------------------

    def get_option(self, opt_str: str) -> Option:
        return self._short_opt.get(opt_str) or self._long_opt.get(opt_str)

    def has_option(self, opt_str: str) -> bool:
        return opt_str in self._short_opt or opt_str in self._long_opt

    def remove_option(self, opt_str: str) -> None:
        option = self._short_opt.get(opt_str)
        if option is None:
            option = self._long_opt.get(opt_str)
        if option is None:
            raise ValueError(f"no such option {opt_str!r}")

        for opt in option._short_opts:
            del self._short_opt[opt]
        for opt in option._long_opts:
            del self._long_opt[opt]
        option.container.option_list.remove(option)

    # -- Help-formatting methods ---------------------------------------

    def format_option_help(self, formatter: HelpFormatter) -> str:
        if not self.option_list:
            return ""
        result = []
        for option in self.option_list:
            if option.help is not SUPPRESS_HELP:
                result.append(formatter.format_option(option))
        return "".join(result)

    def format_description(self, formatter: HelpFormatter) -> str:
        return formatter.format_description(self.get_description())

    def format_help(self, formatter: HelpFormatter) -> str:
        result = []
        if self.description:
            result.append(self.format_description(formatter))
        if self.option_list:
            result.append(self.format_option_help(formatter))
        return "\n".join(result)


class OptionGroup(OptionContainer):
    def __init__(
        self, parser: OptionParser, title: str, description: str | None = None
    ) -> None:
        self.parser: OptionParser = parser
        super().__init__(parser.option_class, parser.conflict_handler, description)
        self.title: str = title
        self.option_list: list[Option] = []

    def _create_option_list(self) -> None:
        self._share_option_mappings(self.parser)

    def set_title(self, title: str) -> None:
        # TODO: property?
        self.title = title

    def destroy(self) -> None:
        """see OptionParser.destroy()."""
        super().destroy()
        del self.option_list

    # -- Help-formatting methods ---------------------------------------

    def format_help(self, formatter: HelpFormatter) -> str:
        result = formatter.format_heading(self.title)
        formatter.indent()
        result += super().format_help(formatter)
        formatter.dedent()
        return result


class OptionParser(OptionContainer):
    """
    Class attributes:
      standard_option_list : [Option]
        list of standard options that will be accepted by all instances
        of this parser class (intended to be overridden by subclasses).

    Instance attributes:
      usage : string
        a usage string for your program.  Before it is displayed
        to the user, "%prog" will be expanded to the name of
        your program (self.prog or os.path.basename(sys.argv[0])).
      prog : string
        the name of the current program (to override
        os.path.basename(sys.argv[0])).
      description : string
        A paragraph of text giving a brief overview of your program.
        optparse reformats this paragraph to fit the current terminal
        width and prints it when the user requests help (after usage,
        but before the list of options).
      epilog : string
        paragraph of help text to print after option help

      option_groups : [OptionGroup]
        list of option groups in this parser (option groups are
        irrelevant for parsing the command-line, but very useful
        for generating help)

      allow_interspersed_args : bool = true
        if true, positional arguments may be interspersed with options.
        Assuming -a and -b each take a single argument, the command-line
          -ablah foo bar -bboo baz
        will be interpreted the same as
          -ablah -bboo -- foo bar baz
        If this flag were false, that command line would be interpreted as
          -ablah -- foo bar -bboo baz
        -- ie. we stop processing options as soon as we see the first
        non-option argument.  (This is the tradition followed by
        Python's getopt module, Perl's Getopt::Std, and other argument-
        parsing libraries, but it is generally annoying to users.)

      process_default_values : bool = true
        if true, option default values are processed similarly to option
        values from the command line: that is, they are passed to the
        type-checking function for the option's type (as long as the
        default value is a string).  (This really only matters if you
        have defined custom types; see SF bug #955889.)  Set it to false
        to restore the behaviour of Optik 1.4.1 and earlier.

      rargs : [string]
        the argument list currently being parsed.  Only set when
        parse_args() is active, and continually trimmed down as
        we consume arguments.  Mainly there for the benefit of
        callback options.
      largs : [string]
        the list of leftover arguments that we have skipped while
        parsing options.  If allow_interspersed_args is false, this
        list is always empty.
      values : Values
        the set of option values currently being accumulated.  Only
        set when parse_args() is active.  Also mainly for callbacks.

    Because of the 'rargs', 'largs', and 'values' attributes,
    OptionParser is not thread-safe.  If, for some perverse reason, you
    need to parse command-line arguments simultaneously in different
    threads, use different OptionParser instances.

    """

    standard_option_list = []
    largs: list[str] | None
    option_groups: list[OptionGroup]
    option_list: list[Option]
    rargs: list[str] | None
    standard_option_list: list[Option]
    values: Values | None

    def __init__(
        self,
        usage: str | None = None,
        option_list: list[OptionGroup] | None = None,
        option_class: type[Option] = Option,
        version: str | None = None,
        conflict_handler: Literal["error", "resolve"] = "error",
        description: str | None = None,
        formatter: HelpFormatter | None = None,
        add_help_option: bool = True,
        prog: str | None = None,
        epilog: str | None = None,
    ) -> None:
        super().__init__(option_class, conflict_handler, description)
        self.set_usage(usage)
        self.prog = prog
        self.version = version
        self.allow_interspersed_args: bool = True
        self.process_default_values: bool = True
        if formatter is None:
            formatter = TitledHelpFormatter()
        self.formatter = formatter
        self.formatter.set_parser(self)
        self.epilog: str | None = epilog

        # Populate the option list; initial sources are the
        # standard_option_list class attribute, the 'option_list'
        # argument, and (if applicable) the _add_version_option() and
        # _add_help_option() methods.
        self._populate_option_list(option_list, add_help=add_help_option)

        self._init_parsing_state()

    def destroy(self) -> None:
        """
        Declare that you are done with this OptionParser.  This cleans up
        reference cycles so the OptionParser (and all objects referenced by
        it) can be garbage-collected promptly.  After calling destroy(), the
        OptionParser is unusable.
        """
        super().destroy()
        for group in self.option_groups:
            group.destroy()
        del self.option_list
        del self.option_groups
        del self.formatter

    # -- Private methods -----------------------------------------------
    # (used by our or OptionContainer's constructor)

    def _create_option_list(self) -> None:
        self.option_list = []
        self.option_groups = []
        self._create_option_mappings()

    def _add_help_option(self) -> None:
        self.add_option(
            "-h", "--help", action="help", help="show this help message and exit"
        )

    def _add_version_option(self) -> None:
        self.add_option(
            "--version",
            action="version",
            help="show program's version number and exit",
        )

    def _populate_option_list(
        self, option_list: list[Option], add_help: bool = True
    ) -> None:
        if self.standard_option_list:
            self.add_options(self.standard_option_list)
        if option_list:
            self.add_options(option_list)
        if self.version:
            self._add_version_option()
        if add_help:
            self._add_help_option()

    def _init_parsing_state(self) -> None:
        # These are set in parse_args() for the convenience of callbacks.
        self.rargs = None
        self.largs = None
        self.values = None

    # -- Simple modifier methods ---------------------------------------

    def set_usage(self, usage: str) -> None:
        if usage is None:
            self.usage = "%prog [options]"
        elif usage is SUPPRESS_USAGE:
            self.usage = None
        # For backwards compatibility with Optik 1.3 and earlier.
        elif usage.lower().startswith("usage: "):
            self.usage = usage[7:]
        else:
            self.usage = usage

    def enable_interspersed_args(self) -> None:
        """Set parsing to not stop on the first non-option, allowing
        interspersing switches with command arguments. This is the
        default behavior. See also disable_interspersed_args() and the
        class documentation description of the attribute
        allow_interspersed_args."""
        self.allow_interspersed_args = True

    def disable_interspersed_args(self) -> None:
        """Set parsing to stop on the first non-option. Use this if
        you have a command processor which runs another command that
        has options of its own and you want to make sure these options
        don't get confused.
        """
        self.allow_interspersed_args = False

    def set_process_default_values(self, process: bool) -> None:
        self.process_default_values = process

    def set_default(self, dest, value) -> None:
        self.defaults[dest] = value

    def set_defaults(self, **kwargs) -> None:
        self.defaults.update(kwargs)

    def _get_all_options(self) -> list[Option]:
        options = self.option_list[:]
        for group in self.option_groups:
            options.extend(group.option_list)
        return options

    def get_default_values(self) -> Values:
        if not self.process_default_values:
            return Values(self.defaults)

        defaults = self.defaults.copy()
        for option in self._get_all_options():
            default = defaults.get(option.dest)
            if isinstance(default, str):
                opt_str = option.get_opt_string()
                defaults[option.dest] = option.check_value(opt_str, default)

        return Values(defaults)

    # -- OptionGroup methods -------------------------------------------

    def add_option_group(self, *args, **kwargs) -> OptionGroup:
        # XXX lots of overlap with OptionContainer.add_option()
        if isinstance(args[0], str):
            group = OptionGroup(self, *args, **kwargs)
        elif len(args) == 1 and not kwargs:
            group = args[0]
            if not isinstance(group, OptionGroup):
                raise TypeError(f"not an OptionGroup instance: {group!r}")
            if group.parser is not self:
                raise ValueError("invalid OptionGroup (wrong parser)")
        else:
            raise TypeError("invalid arguments")

        self.option_groups.append(group)
        return group

    def get_option_group(self, opt_str: str) -> OptionGroup | None:
        option = self._short_opt.get(opt_str) or self._long_opt.get(opt_str)
        if option and option.container is not self:
            return option.container
        return None

    # -- Option-parsing methods ----------------------------------------

    def _get_args(self, args: list[str]) -> list[str]:
        # TODO: remove?
        if args is None:
            return sys.argv[1:]
        return args[:]  # don't modify caller's list

    # @overload
    # def parse_args(self, args: None = None, values: Values | None = None) -> tuple[Values, list[str]]:
    #     ...
    #
    # @overload
    # def parse_args(self, args: Sequence[AnyStr], values: Values | None = None) -> tuple[Values, list[AnyStr]]:
    #     ...

    def parse_args(
        self, args: Iterable[str] | None = None, values: Values | None = None
    ) -> tuple[Values, list[str]]:
        """
        parse_args(args : [string] = sys.argv[1:],
                   values : Values = None)
        -> (values : Values, args : [string])

        Parse the command-line options found in 'args' (default:
        sys.argv[1:]).  Any errors result in a call to 'error()', which
        by default prints the usage message to stderr and calls
        sys.exit() with an error message.  On success returns a pair
        (values, args) where 'values' is a Values instance (with all
        your option values) and 'args' is the list of arguments left
        over after parsing options.
        """
        if args:
            args = args[:]
        rargs = args or sys.argv[1:]
        values = values or self.get_default_values()

        # Store the halves of the argument list as attributes for the
        # convenience of callbacks:
        #   rargs
        #     the rest of the command-line (the "r" stands for
        #     "remaining" or "right-hand")
        #   largs
        #     the leftover arguments -- ie. what's left after removing
        #     options and their arguments (the "l" stands for "leftover"
        #     or "left-hand")
        self.rargs = rargs
        self.largs = largs = []
        self.values = values

        try:
            self._process_args(largs, rargs, values)
        except (BadOptionError, OptionValueError) as err:
            self.error(str(err))

        args = largs + rargs
        return self.check_values(values, args)

    def check_values(self, values: Values, args: list[str]) -> tuple[Values, list[str]]:
        """
        check_values(values : Values, args : [string])
        -> (values : Values, args : [string])

        Check that the supplied option values and leftover arguments are
        valid.  Returns the option values and leftover arguments
        (possibly adjusted, possibly completely new -- whatever you
        like).  Default implementation just returns the passed-in
        values; subclasses may override as desired.
        """
        return (values, args)

    def _process_args(self, largs: list[str], rargs: list[str], values: Values) -> None:
        """_process_args(largs : [string],
                         rargs : [string],
                         values : Values)

        Process command-line arguments and populate 'values', consuming
        options and arguments from 'rargs'.  If 'allow_interspersed_args' is
        false, stop at the first non-option argument.  If true, accumulate any
        interspersed non-option arguments in 'largs'.
        """
        while rargs:
            arg = rargs[0]
            # We handle bare "--" explicitly, and bare "-" is handled by the
            # standard arg handler since the short arg case ensures that the
            # len of the opt string is greater than 1.
            if arg == "--": # REMAINDER
                del rargs[0]
                return
            if arg[0:2] == "--":
                # process a single long option (possibly with value(s))
                self._process_long_opt(rargs, values)
            elif arg[:1] == "-" and len(arg) > 1:
                # process a cluster of short options (possibly with
                # value(s) for the last one only)
                self._process_short_opts(rargs, values)
            elif self.allow_interspersed_args:
                largs.append(arg)
                del rargs[0]
            else:
                return  # stop now, leave this arg in rargs

        # Say this is the original argument list:
        # [arg0, arg1, ..., arg(i-1), arg(i), arg(i+1), ..., arg(N-1)]
        #                             ^
        # (we are about to process arg(i)).
        #
        # Then rargs is [arg(i), ..., arg(N-1)] and largs is a *subset* of
        # [arg0, ..., arg(i-1)] (any options and their arguments will have
        # been removed from largs).
        #
        # The while loop will usually consume 1 or more arguments per pass.
        # If it consumes 1 (eg. arg is an option that takes no arguments),
        # then after _process_arg() is done the situation is:
        #
        #   largs = subset of [arg0, ..., arg(i)]
        #   rargs = [arg(i+1), ..., arg(N-1)]
        #
        # If allow_interspersed_args is false, largs will always be
        # *empty* -- still a subset of [arg0, ..., arg(i-1)], but
        # not a very interesting subset!

    def _match_long_opt(self, opt: str) -> str:
        """_match_long_opt(opt : string) -> string

        Determine which long option string 'opt' matches, ie. which one
        it is an unambiguous abbreviation for.  Raises BadOptionError if
        'opt' doesn't unambiguously match any long option string.
        """
        return _match_abbrev(opt, self._long_opt)

    def _process_long_opt(self, rargs: list[str], values: Values) -> None:
        arg = rargs.pop(0)

        # Value explicitly attached to arg?  Pretend it's the next
        # argument.
        if "=" in arg:
            (opt, next_arg) = arg.split("=", 1)
            rargs.insert(0, next_arg)
            had_explicit_value = True
        else:
            opt = arg
            had_explicit_value = False

        opt = self._match_long_opt(opt)
        option = self._long_opt[opt]
        if option.takes_value():
            nargs = option.nargs
            if len(rargs) < nargs:
                message = f"{opt!s} option requires {nargs:d} argument"
                message = f"{message}s" if nargs > 1 else message
                self.error(message)
            elif nargs == 1:
                value = rargs.pop(0)
            else:
                value = tuple(rargs[0:nargs])
                del rargs[0:nargs]

        elif had_explicit_value:
            self.error(f"{opt!s} option does not take a value")

        else:
            value = None

        option.process(opt, value, values, self)

    def _process_short_opts(self, rargs: list[str], values: Values) -> None:
        arg = rargs.pop(0)
        stop = False
        i = 1
        for ch in arg[1:]:
            opt = "-" + ch
            option = self._short_opt.get(opt)
            i += 1  # we have consumed a character

            if not option:
                raise BadOptionError(opt)
            if option.takes_value():
                # Any characters left in arg?  Pretend they're the
                # next arg, and stop consuming characters of arg.
                if i < len(arg):
                    rargs.insert(0, arg[i:])
                    stop = True

                nargs = option.nargs
                if len(rargs) < nargs:
                    msg = f"{opt!s} option requires {nargs:d} argument"
                    message = msg if nargs == 1 else f"{msg}s"
                    self.error(message)
                elif nargs == 1:
                    value = rargs.pop(0)
                else:
                    value = tuple(rargs[0:nargs])
                    del rargs[0:nargs]

            else:  # option doesn't take a value
                value = None

            option.process(opt, value, values, self)

            if stop:
                break

    # -- Feedback methods ----------------------------------------------

    def get_prog_name(self) -> str:
        if self.prog is None:
            return os.path.basename(sys.argv[0])
        return self.prog

    def expand_prog_name(self, s: str) -> str:
        return s.replace("%prog", self.get_prog_name())

    def get_description(self) -> str:
        return self.expand_prog_name(self.description)

    def exit(self, status: int = 0, msg: str | None = None) -> NoReturn:
        if msg:
            sys.stderr.write(msg)
        sys.exit(status)

    def error(self, msg: str) -> NoReturn:
        """error(msg : string)

        Print a usage message incorporating 'msg' to stderr and exit.
        If you override this in a subclass, it should not return -- it
        should either exit or raise an exception.
        """
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.get_prog_name()}: error: {msg}\n")

    def get_usage(self) -> str:
        if self.usage:
            return self.formatter.format_usage(self.expand_prog_name(self.usage))
        return ""

    def print_usage(self, file: IO[str] | None = None) -> None:
        """print_usage(file : file = stdout)

        Print the usage message for the current program (self.usage) to
        'file' (default stdout).  Any occurrence of the string "%prog" in
        self.usage is replaced with the name of the current program
        (basename of sys.argv[0]).  Does nothing if self.usage is empty
        or not defined.
        """
        if self.usage:
            print(self.get_usage(), file=file)

    def get_version(self) -> str:
        if self.version:
            return self.expand_prog_name(self.version)
        return ""

    def print_version(self, file: IO[str] | None = None) -> None:
        """print_version(file : file = stdout)

        Print the version message for this program (self.version) to
        'file' (default stdout).  As with print_usage(), any occurrence
        of "%prog" in self.version is replaced by the current program's
        name.  Does nothing if self.version is empty or undefined.
        """
        if self.version:
            print(self.get_version(), file=file)

    def format_option_help(self, formatter: HelpFormatter | None = None) -> str:
        formatter = formatter or self.formatter
        formatter.store_option_strings(self)
        result = []
        result.append(formatter.format_heading("Options"))
        formatter.indent()
        if self.option_list:
            result.append(super().format_option_help(formatter))
            result.append("\n")
        for group in self.option_groups:
            result.append(group.format_help(formatter))
            result.append("\n")
        formatter.dedent()
        # Drop the last "\n", or the header if no options or option groups:
        return "".join(result[:-1])

    def format_epilog(self, formatter: HelpFormatter) -> str:
        return formatter.format_epilog(self.epilog)

    def format_help(self, formatter: HelpFormatter | None = None) -> str:
        if formatter is None:
            formatter = self.formatter
        result = []
        if self.usage:
            result.append(self.get_usage() + "\n")
        if self.description:
            result.append(self.format_description(formatter) + "\n")
        result.append(self.format_option_help(formatter))
        result.append(self.format_epilog(formatter))
        return "".join(result)

    def print_help(self, file: IO[str] | None = None) -> None:
        """print_help(file : file = stdout)

        Print an extended help message, listing all options and any
        help text provided with them, to 'file' (default stdout).
        """
        if file is None:
            file = sys.stdout
        file.write(self.format_help())


# class OptionParser


def _match_abbrev(s: str, wordmap: dict[str, Option]) -> str:
    """_match_abbrev(s : string, wordmap : {string : Option}) -> string

    Return the string key in 'wordmap' for which 's' is an unambiguous
    abbreviation.  If 's' is found to be ambiguous or doesn't match any of
    'words', raise BadOptionError.
    """
    # Is there an exact match?
    if s in wordmap:
        return s
    # Isolate all words with s as a prefix.
    possibilities = [word for word in wordmap if word.startswith(s)]
    # No exact match, so there had better be just one possibility.
    if len(possibilities) == 1:
        return possibilities[0]
    if not possibilities:
        raise BadOptionError(s)
    # More than one possible completion: ambiguous prefix.
    possibilities.sort()
    raise AmbiguousOptionError(s, possibilities)
