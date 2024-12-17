from datetime import datetime, timedelta
from functools import wraps
from inspect import stack
from pathlib import Path
import json
import py_common.log as log


def cache_to_disk(key: str, ttl: int):
    """
    Caches the result of the decorated function for ttl seconds

    Does not account for function parameters!
    """
    paths = [frame.filename for frame in stack() if not frame.filename.startswith("<")]
    if len(paths) < 2:
        log.warning(
            "Expected at least 2 paths in the stack: "
            "the current file and the script that called it"
        )

    cache_file = Path(paths[1]).absolute().with_name("cache.json")

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                data = json.loads(cache_file.read_text(encoding="utf-8"))
            except FileNotFoundError:
                data = {}
            except json.JSONDecodeError | UnicodeDecodeError:
                log.error(f"Failed to parse cache file '{cache_file}'")
                return func(*args, **kwargs)

            if (
                key in data
                and datetime.fromisoformat(data[key]["timestamp"]) > datetime.now()
            ):
                log.debug(f"Using cached value for {key}")
                return data[key]["data"]

            result = func(*args, **kwargs)
            data[key] = {
                "timestamp": (datetime.now() + timedelta(seconds=ttl)).isoformat(),
                "data": result,
            }
            json_data = json.dumps(data, ensure_ascii=False, indent=2)
            cache_file.write_text(json_data, encoding="utf-8")
            return result

        def clear():
            log.debug("Clearing cache")
            cache_file.unlink()

        wrapper.clear_cache = clear  # type: ignore
        return wrapper

    return decorator
