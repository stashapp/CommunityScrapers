# Log messages are transmitted via stderr and are
# encoded with a prefix consisting of special character SOH, then the log
# level (one of t, d, i, w, e - corresponding to trace, debug, info,
# warning and error levels respectively), then special character
# STX.
#
# The log.trace, log.debug, log.info, log.warning, and log.error methods, and their equivalent
# formatted methods are intended for use by script scraper instances to transmit log
# messages.

import re, sys, copy, json

def __prefix(levelChar):
    startLevelChar = b'\x01'
    endLevelChar = b'\x02'

    ret = startLevelChar + levelChar + endLevelChar
    return ret.decode()

def __log(levelChar, s):
    s_out = copy.deepcopy(s)
    
    if isinstance(s_out, dict):
        s_out = json.dumps(s_out)

    if not isinstance(s_out, str):
        s_out = str(s_out)
    s_out = re.sub(r'(?<=")(data:image.+?;base64).+?(?=")', r'\1;truncated', s_out)

    if levelChar == "":
        return

    print(__prefix(levelChar) + s_out + "\n", file=sys.stderr, flush=True)

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