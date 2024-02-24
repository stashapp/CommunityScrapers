from inspect import stack
from pathlib import Path

import py_common.log as log


def get_config(default: str | None = None) -> "CustomConfig":
    """
    Gets the config for the currently executing script, taking a default config as a fallback:
    This allows scrapers to define their own configuration options in a way that lets them
    persist across reinstalls

    The default config must have the same format as a simple .ini config file consisting of
    key-value pairs separated by an equals sign, and can optionally contain comments and blank lines
    for readability
    """
    config = CustomConfig(default)
    if not default:
        log.warning("No config specified")
        return config

    # Note: chained configs were removed until we find a use case for them

    # The paths of every script in the callstack: in the above example this would be:
    # this script                    the api script              the site script
    # "/scrapers/py_common/util.py", "/scrapers/api/scraper.py", "/scrapers/site/site.py"
    # In a single script scraper this would just be:
    # this script                    the site script
    # "/scrapers/py_common/util.py", "/scrapers/site/site.py"
    paths = [frame.filename for frame in stack() if not frame.filename.startswith("<")]
    if len(paths) < 2:
        log.warning(
            "Expected at least 2 paths in the stack: "
            "the current file and the script that called it"
        )
        log.warning("Not persisting config")
        return config

    # We can output the path of the script that called this function
    # to help with debugging config issues
    current_path = Path(paths[1]).absolute()
    prefix = str(Path(current_path.parent.name, current_path.name))

    configs = [Path(p).parent / ("config.ini") for p in paths][1:]

    # See git history if you want the chained configs version
    config_path = configs[0]
    if not config_path.exists():
        log.debug(f"[{prefix}] First run, creating default config at {config_path}")
        config_path.write_text(str(config))
    else:
        log.debug(f"[{prefix}] Reading config from {config_path}")
        config.update(config_path.read_text())

    return config


class Chunk:
    def __init__(self, raw: list[str]):
        self.comments = []
        self.key = self.value = None
        for line in raw:
            if not line or line.startswith("#"):
                self.comments.append(line)
            elif "=" in line:
                key, value = [x.strip() for x in line.split("=", 1)]
                if not key.isidentifier():
                    log.warning(f"Config key '{key}' is not a valid identifier")
                self.key = key
                self.value = self.__parse_value(value)
            else:
                log.warning(f"Ignoring invalid config line: {line}")

    def __parse_value(self, value):
        if value.lower() == "true":
            return True
        elif value.lower() == "false":
            return False
        elif "." in value:
            try:
                return float(value)
            except ValueError:
                return value
        elif value.isdigit():
            return int(value)
        else:
            return value


def chunkify(config_string):
    chunks = []
    current_chunk = []
    if not config_string:
        return chunks, current_chunk

    for lineno, line in enumerate(config_string.strip().splitlines()):
        line = line.strip()
        current_chunk.append(line)

        if "=" in line:
            chunks.append(Chunk(current_chunk))
            current_chunk = []
        elif not line.startswith("#") and line:
            log.warning(f"Ignoring invalid config line {lineno}: {line}")
    return chunks, current_chunk


class CustomConfig:
    """
    Custom config parser that stores comments associated with each key

    Settings must be in the format:
    ```ini
    # optional comment
    key = value
    ```
    """

    def __init__(self, config_string: str | None = None):
        chunks, trailing_comments = chunkify(config_string)
        self.config_dict = {chunk.key: chunk.value for chunk in reversed(chunks)}
        self.comments = {chunk.key: chunk.comments for chunk in chunks}
        self.trailing_comments = trailing_comments

    def update(self, config_string: str):
        new_chunks, new_trailing_comments = chunkify(config_string)
        for chunk in new_chunks:
            if chunk.key not in self.config_dict:
                self.comments[chunk.key] = chunk.comments
            self.config_dict[chunk.key] = chunk.value
        for line in new_trailing_comments:
            if line not in self.trailing_comments:
                self.trailing_comments.append(line)

    def __getattr__(self, name):
        if name in self.config_dict:
            return self.config_dict[name]
        raise AttributeError(
            f"'{type(self).__name__}' object has no attribute '{name}'"
        )

    def __getitem__(self, name):
        return self.config_dict[name]

    def __str__(self):
        "Generate a string representation of the configuration"
        lines = []
        for key, value in reversed(self.config_dict.items()):
            # Add comments associated with the key
            lines.extend(self.comments[key])
            lines.append(f"{key} = {value}")
        lines.extend(reversed(self.trailing_comments))
        return "\n".join(lines)
