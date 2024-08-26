import sys
import subprocess
import re
from pathlib import Path
from inspect import stack

from py_common import log


def _parse_package(specifier: str) -> tuple[str, str, str] | None:
    """
    Parses a package specifier in the format "import_name:package_name==version"
    and returns a tuple of (package_name, version, import_name)

    >>> parse_package("requests==2.26.0")
    ('requests', '2.26.0', 'requests')
    >>> parse_package("bs4:beautifulsoup4")
    ('beautifulsoup4', '', 'bs4')
    """
    match = re.match(
        r"^(?:(?P<import_name>[^:]+):)?(?P<package_name>[^=]+)(?:==(?P<version>.+))?$",
        specifier,
    )
    if not match:
        return None

    return (
        match.group("package_name"),
        match.group("version") or "",
        match.group("import_name") or match.group("package_name"),
    )


def ensure_requirements(*deps: str):
    """
    Ensures that the given dependencies are installed for the current scraper

    For packages that have different import names than their package names, you can specify
    the import name and package name separated by a colon, e.g. "bs4:beautifulsoup4"

    To install a package with a specific version, you can specify the version
    after the package name, e.g. "requests==2.26.0"
    """
    paths = [frame.filename for frame in stack() if not frame.filename.startswith("<")]
    if len(paths) < 2:
        log.warning(
            "Expected at least 2 paths in the stack: "
            "the current file and the script that called it"
        )
        log.warning("Not installing dependencies")
        return

    current_path = Path(paths[1]).absolute()

    parsed_deps = {dep: _parse_package(dep) for dep in deps}

    deps_folder = current_path.parent.parent / "automatic_dependencies"
    sys.path.insert(0, str(deps_folder))

    try:
        import importlib

        for specifier, parsed in parsed_deps.items():
            if not parsed:
                log.warning(f"Ignoring invalid package specifier: {specifier}")
                continue
            _, version, import_name = parsed
            module = importlib.import_module(import_name)
            if version and module.__version__ != version:
                log.warning(
                    f"'{import_name}' {module.__version__} != {version}, bailing out"
                )
                return
        # All deps found, no need to reinstall
        return
    except ImportError as e:
        log.debug(f"Failed to import '{e.name}'")

    package_names = [parsed[0] for parsed in parsed_deps.values() if parsed]
    log.warning(f"Installing dependencies: {', '.join(package_names)}")
    log.warning(
        "This can take a while! If you install the dependencies manually "
        "you can avoid this step in the future"
    )

    deps_folder.mkdir(exist_ok=True)
    subprocess.check_call(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--no-input",
            f"--target={deps_folder}",
            *package_names,
        ],
        stdout=subprocess.DEVNULL,
    )

    importlib.invalidate_caches()
    log.warning(f"Dependencies installed successfully into {deps_folder}")
