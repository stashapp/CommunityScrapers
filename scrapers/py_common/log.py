import sys
import re
import traceback
from functools import partial
# Log messages sent from a script scraper instance are transmitted via stderr and are
# encoded with a prefix consisting of special character SOH, then the log
# level (one of t, d, i, w or e - corresponding to trace, debug, info,
# warning and error levels respectively), then special character
# STX.
#
# The log.trace, log.debug, log.info, log.warning, and log.error methods, and their equivalent
# formatted methods are intended for use by script scraper instances to transmit log
# messages.


def __log(level_char: str, s):
    lvl_char = "\x01{}\x02".format(level_char)
    s = re.sub(r"data:.+?;base64[^'\"]+", "[...]", str(s))
    for line in s.splitlines():
        print(lvl_char, line, file=sys.stderr, flush=True)


trace = partial(__log, "t")
debug = partial(__log, "d")
info = partial(__log, "i")
warning = partial(__log, "w")
error = partial(__log, "e")


# Uncaught exceptions will result in unmarshaling errors which are not helpful
# so we hook into the exception printing machinery: if a user reports a failure
# with exit code 69 we can assume an uncaught exception instead of something like
# an accidental print statement or malformed JSON output
# Also prints the current Python version and executable path for debugging
def custom_excepthook(exc_type, exc_value, exc_traceback):
    error(f"Running Python {sys.version} at {sys.executable}")
    for line in traceback.format_exception(exc_type, exc_value, exc_traceback):
        error(line)
    print("null")
    exit(69)


# Assumption: only Stash will pipe into stdin
if not sys.stdin.isatty():
    sys.excepthook = custom_excepthook
