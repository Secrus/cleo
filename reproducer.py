from __future__ import annotations

from cleo.io.buffered_io import BufferedIO
from cleo.ui.exception_trace.component import ExceptionTrace
from cleo.ui.exception_trace.inspector import Inspector

if __name__ == "__main__":
    io = BufferedIO()

    try:
        try:
            raise ValueError("ValueError")
        except ValueError:
            raise RuntimeError("RuntimeError") from None
    except Exception as e:
        # assert the condition
        assert e.__context__ is not None
        print("e context: ", e.__context__)
        assert e.__suppress_context__
        print("e suppress context: ", e.__suppress_context__)

        # this is the high level impact
        ExceptionTrace(e).render(io)

        # this is the root cause
        assert not Inspector(e).has_previous_exception()
    finally:
        output = io.fetch_output()
        #print(output)

        # if __suppress_context__ is respected this should not be displayed
        assert "The following error occurred when trying to handle this error:" not in output
