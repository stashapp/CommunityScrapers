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

    If a script is calling another script, this will merge all config files in the stack
    Example: Scraping a scene with Brazzers, which has `scrape_markers = True` in its config
    while AyloAPI has `scrape_markers = False` in its config

    Brazzers/Brazzers.py calls AyloAPI/scrape.py
    The config for Brazzers has higher precedence than the config for AyloAPI,
    so the final config will have scrape_markers = True
    """
    config = CustomConfig(default)
    if not default:
        log.warning("No default config specified")
        return config

    # The paths of every script in the stack:
    # "/scrapers/py_common/util.py", "/scrapers/api/scraper.py", "/scrapers/site/site.py"
    paths = [frame.filename for frame in stack() if not frame.filename.startswith("<")]
    if len(paths) < 2:
        log.warning(
            "Expected at least 2 paths in the stack: "
            "the current file and the script that called it"
        )
        log.warning("Not persisting config")
        return config

    # We can output the path of the current script to help with debugging config issues
    current_path = Path(paths[1]).absolute()
    prefix = str(Path(current_path.parent.name, current_path.name))

    # Skip the py_common util file: we don't want to mess with this config
    # Path("/scrapers/api/config.ini"), Path("/scrapers/site/config.ini")
    configs = [Path(p).parent / ("config.ini") for p in paths][1:]

    # Update our config with the values from each config file, so that the
    # most specific config overrides the more general ones
    # /scrapers/site/config.ini is more specific than /scrapers/api/config.ini
    for config_path in configs:
        if config_path.exists():
            log.debug(f"[{prefix}] Reading config from {config_path}")
            config.update(config_path.read_text())
        else:
            log.debug(f"[{prefix}] Creating default config at {config_path}")
            config_path.write_text(str(config))
        if "py_common" in config_path.parts:
            # py_common should not merge configs
            break

    log.debug(str(config))
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
    for line in config_string.strip().splitlines():
        line = line.strip()
        current_chunk.append(line)

        if "=" in line:
            chunks.append(Chunk(current_chunk))
            current_chunk = []
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
