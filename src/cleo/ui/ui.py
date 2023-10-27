from __future__ import annotations

from typing import TYPE_CHECKING

from cleo.terminal import Terminal


if TYPE_CHECKING:
    from cleo.io.io import IO


class UI:
    def __init__(self, io: IO | None = None, terminal: Terminal | None = None) -> None:
        self._io = io  # TODO: or default IO object
        self._terminal = terminal or Terminal()

    def write(self):
        pass

    def write_line(self):
        pass

    def ask(self, *, confirm, secret, choice):
        pass

    def exception_trace(self):
        pass

    def choice_question(self):
        pass

    def confirmation_question(self):
        pass

    def progress_bar(self):
        pass

    def progress_indicator(self):
        pass

    def table(self):
        pass

    def spinner(self):
        pass

    # def confirm(
    #     self, question: str, default: bool = False, true_answer_regex: str = r"(?i)^y"
    # ) -> bool:
    #     """
    #     Confirm a question with the user.
    #     """
    #     from cleo.ui.components.confirmation_question import ConfirmationQuestion
    #
    #     confirmation = ConfirmationQuestion(
    #         question, default=default, true_answer_regex=true_answer_regex
    #     )
    #     return cast(bool, confirmation.ask(self._io))
    #
    #
    #
    # def ask(self, question: str | Question, default: Any | None = None) -> Any:
    #     """
    #     Prompt the user for input.
    #     """
    #     from cleo.ui.components.question import Question
    #
    #     if not isinstance(question, Question):
    #         question = Question(question, default=default)
    #
    #     return question.ask(self._io)
    #
    # def secret(self, question: str | Question, default: Any | None = None) -> Any:
    #     """
    #     Prompt the user for input but hide the answer from the console.
    #     """
    #     from cleo.ui.components.question import Question
    #
    #     if not isinstance(question, Question):
    #         question = Question(question, default=default)
    #
    #     question.hide()
    #
    #     return question.ask(self._io)
    #
    # def choice(
    #     self,
    #     question: str,
    #     choices: list[str],
    #     default: Any | None = None,
    #     attempts: int | None = None,
    #     multiple: bool = False,
    # ) -> Any:
    #     """
    #     Give the user a single choice from an list of answers.
    #     """
    #     from cleo.ui.components.choice_question import ChoiceQuestion
    #
    #     choice = ChoiceQuestion(question, choices, default)
    #
    #     choice.set_max_attempts(attempts)
    #     choice.set_multi_select(multiple)
    #
    #     return choice.ask(self._io)
    #
    # def create_question(
    #     self,
    #     question: str,
    #     type: Literal[choice, confirmation] | None = None,
    #     **kwargs: Any,
    # ) -> Question:
    #     """
    #     Returns a Question of specified type.
    #     """
    #     from cleo.ui.components.choice_question import ChoiceQuestion
    #     from cleo.ui.components.confirmation_question import ConfirmationQuestion
    #     from cleo.ui.components.question import Question
    #
    #     if type == "confirmation":
    #         return ConfirmationQuestion(question, **kwargs)
    #
    #     if type == "choice":
    #         return ChoiceQuestion(question, **kwargs)
    #
    #     return Question(question, **kwargs)
    #
    # def table(
    #     self,
    #     header: str | None = None,
    #     rows: Rows | None = None,
    #     style: str | None = None,
    # ) -> Table:
    #     """
    #     Return a Table instance.
    #     """
    #     from cleo.ui.components.table import Table
    #
    #     table = Table(self._io, style=style)
    #
    #     if header:
    #         table.set_headers([header])
    #
    #     if rows:
    #         table.set_rows(rows)
    #
    #     return table
    #
    # def progress_bar(self, max: int = 0) -> ProgressBar:
    #     """
    #     Creates a new progress bar
    #     """
    #     from cleo.ui.components.progress_bar import ProgressBar
    #
    #     return ProgressBar(self._io, max=max)
    #
    # def progress_indicator(
    #     self,
    #     fmt: str | None = None,
    #     interval: int = 100,
    #     values: list[str] | None = None,
    # ) -> ProgressIndicator:
    #     """
    #     Creates a new progress indicator.
    #     """
    #     from cleo.ui.components.progress_indicator import ProgressIndicator
    #
    #     return ProgressIndicator(self.io, fmt, interval, values)
    #
    # def spin(
    #     self,
    #     start_message: str,
    #     end_message: str,
    #     fmt: str | None = None,
    #     interval: int = 100,
    #     values: list[str] | None = None,
    # ) -> ContextManager[ProgressIndicator]:
    #     """
    #     Automatically spin a progress indicator.
    #     """
    #     spinner = self.progress_indicator(fmt, interval, values)
    #
    #     return spinner.auto(start_message, end_message)
