from datetime import datetime, timedelta
from functools import wraps
import hashlib
from inspect import stack
from pathlib import Path
import json
import threading
import py_common.log as log

_locks: dict[Path, threading.Lock] = {}
_locks_guard = threading.Lock()


def _lock_for(path: Path) -> threading.Lock:
    "One lock per cache file, shared by every function decorated for that file."
    with _locks_guard:
        return _locks.setdefault(path, threading.Lock())


def _read_cache(cache_file: Path) -> dict:
    try:
        return json.loads(cache_file.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except (json.JSONDecodeError, UnicodeDecodeError):
        log.error(f"Failed to parse cache file '{cache_file}'")
        return {}


def cache_to_disk(ttl: int):
    """
    Caches the result of the decorated function for ttl seconds
    """
    paths = [frame.filename for frame in stack() if not frame.filename.startswith("<")]
    if len(paths) < 2:
        log.warning(
            "Expected at least 2 paths in the stack: "
            "the current file and the script that called it"
        )

    cache_file = Path(paths[1]).absolute().with_name("cache.json")
    lock = _lock_for(cache_file)

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Use the args to generate a synthetic cache key
            args_tuple = (args, sorted(kwargs.items()))
            args_hash = hashlib.sha256(
                json.dumps(args_tuple).encode("utf-8")
            ).hexdigest()
            synthetic_key = f"{func.__name__}_{args_hash}"

            with lock:
                data = _read_cache(cache_file)
                if (
                    synthetic_key in data
                    and datetime.fromisoformat(data[synthetic_key]["expires"])
                    > datetime.now()
                ):
                    log.debug(f"Using cached value for {synthetic_key}")
                    return data[synthetic_key]["data"]

            # do the actual (potentially slow) work outside the lock, so
            # concurrent calls for different cache keys aren't serialized on
            # each other's network I/O - only the file read/write is
            result = func(*args, **kwargs)

            with lock:
                # re-read rather than reusing the copy from above: another
                # thread may have written its own entry to this same file
                # while this thread's call was in flight
                data = _read_cache(cache_file)
                data[synthetic_key] = {
                    "expires": (datetime.now() + timedelta(seconds=ttl)).isoformat(),
                    "data": result,
                }
                json_data = json.dumps(data, ensure_ascii=False, indent=2)
                cache_file.write_text(json_data, encoding="utf-8")
            return result

        return wrapper

    return decorator
