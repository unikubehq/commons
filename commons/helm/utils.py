import logging
import os
import re
import subprocess

from commons.helm.exceptions import HelmDependencyError

logger = logging.getLogger("projects.helm")


def execute(cmd, cwd, env=None) -> subprocess.Popen:
    """
    Executes a command in a directory with a certain environment

    :returns Popen
    """
    kwargs = {"encoding": "utf-8", "stdout": subprocess.PIPE}
    process = subprocess.Popen(cmd, cwd=cwd, env=env, **kwargs)
    try:
        process.wait()
    except KeyboardInterrupt:
        try:
            process.terminate()
        except OSError:
            pass
        process.wait()
    return process


def install_dependencies(directory):
    """Install dependencies for helm charts."""
    logger.debug(f"Running `helm dep up` inside {directory}")
    process = execute(["helm", "dep", "up"], cwd=directory)
    return process.returncode == 0


def dependency_update_required(directory):
    """Check whether helm charts' dependencies need to be updated."""
    process = execute(["helm", "dep", "list"], cwd=directory)
    if process.returncode == 0:
        output_lines = process.stdout.readlines()[1:]
        col_re = r"\s*([\w\.]+)\s*"
        for line in output_lines:
            status = re.findall(col_re, line)
            if status:
                if status[-1] == "ok":
                    continue
                else:
                    return True
    return False


def check_helm_dependencies(directory):
    """Update helm charts' dependencies if needed."""
    if dependency_update_required(directory):
        if not install_dependencies(directory):
            raise HelmDependencyError(f"could not build dependencies in {directory}")
    else:
        logger.debug("dep update not required")


def get_command(output_dir, values, name, chart, *args, secrets=False):
    # command is: helm template [NAME] [CHART] [flags]
    command = ["helm"]

    if os.path.isdir(values):
        command.append("multivalues")

    if secrets:
        command.append("secrets")

    command.append("template")
    command.extend(["--output-dir", output_dir])
    command.extend(args)

    command.extend(
        [
            name,
            chart,
            "-f",
            values,
        ]
    )
    return command


# kudos https://www.peterbe.com/plog/fastest-python-function-to-slugify-a-string
non_url_safe = [
    '"',
    "#",
    "$",
    "%",
    "&",
    "+",
    ",",
    "/",
    ":",
    ";",
    "=",
    "?",
    "@",
    "[",
    "\\",
    "]",
    "^",
    "`",
    "{",
    "|",
    "}",
    "~",
    "'",
]


def slugify(text):
    """
    Turn the text content of a header into a slug for use in an ID
    """
    non_safe = [c for c in text if c in non_url_safe]
    if non_safe:
        for c in non_safe:
            text = text.replace(c, "")
    # Strip leading, trailing and multiple whitespace, convert remaining whitespace to _
    text = "_".join(text.split())
    return text
