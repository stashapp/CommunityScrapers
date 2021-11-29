import sys

# Log messages sent from a plugin instance are transmitted via stderr and are
# encoded with a prefix consisting of special character SOH, then the log
# level (one of t, d, i, w or e - corresponding to trace, debug, info,
# warning, error levels respectively), then special character
# STX.
#
# The LogTrace, LogDebug, LogInfo, LogWarning, and LogError methods, and their equivalent
# formatted methods are intended for use by plugin instances to transmit log
# messages.
#

def __log(level_char: bytes, s):
    if level_char:
        lvl_char = "\x01{}\x02".format(level_char.decode())
        s = re.sub(r"data:image.+?;base64(.+?')","[...]",str(s))
        for x in s.split("\n"):
            print(lvl_char, x, file=sys.stderr, flush=True)


def trace(s):
    __log(b't', s)


def debug(s):
    __log(b'd', s)


def info(s):
    __log(b'i', s)


def warning(s):
    __log(b'w', s)


def error(s):
    __log(b'e', s)
