import logging
import os
import re
import subprocess
import tempfile

from commons.helm.data_classes import DeckData, SopsProviderType
from commons.helm.exceptions import HelmChartRenderError, HelmDependencyError

logger = logging.getLogger("projects.helm")


class HelmCharts:
    """Renders helm charts and provides path to rendered output.

    Can be used as a context manager:
    with HelmCharts(repository_directory, deck) as dir:
        for root, dirs, files in os.walk(dir):
            ...
    """

    def __init__(self, repository_directory, deck: DeckData, values_path: str):
        self.directory = repository_directory
        self.deck = deck
        self.values_path = values_path

    def __enter__(self):
        command = self._get_command()
        env = self._get_env()

        logger.debug(f"running: {command}, in dir {self.directory}")
        process = self._execute(command, cwd=self.directory, env=env)
        logger.debug(f"helm 'template' process ended with: {process.returncode}")

        if process.returncode == 0:
            return self.rendered_chart_dir.name

        raise HelmChartRenderError(process.stdout.read())

    def __exit__(self, type, value, traceback):
        self.rendered_chart_dir.cleanup()

    def _get_env(self):
        """Create environment dictionary."""
        env = os.environ.copy()
        if self.deck.sops:
            if self.deck.sops.type == SopsProviderType.PGP:
                self._prepare_gpg(self.deck.sops.get_env())
            elif self.deck.sops.type == SopsProviderType.AWS:
                env.update(self.deck.sops.get_env())

        # we must set all values to strings, otherwise expect errors
        env = {k: str(v) for k, v in env.items()}
        return env

    def _get_parameters(self):
        """Generate list of parameters for `helm template` command."""
        params = []
        if self.deck.namespace:
            params.extend([f"--namespace={self.deck.namespace}"])
        return params

    def _get_command(self):
        """Generate `helm` command based on given deck and its values."""
        command = ["helm"]

        # deck.values starts with /. That needs to be excluded.
        values = os.path.join(self.directory, self.values_path.lstrip("/"))
        if os.path.isdir(values):
            command.append("multivalues")

        if self.deck.sops:
            command.append("secrets")

        self._check_helm_dependencies(self.deck, self.directory)

        self.rendered_chart_dir = tempfile.TemporaryDirectory()
        logger.debug("created temporary directory:" + str(self.rendered_chart_dir.name))
        # chain the entire helm command to build the charts
        command.append("template")
        command.extend(["--output-dir", self.rendered_chart_dir.name])
        command.extend(self._get_parameters())
        command.extend(
            [
                self.deck.title,
                f"{self.deck.title}/",
                "-f",
                values,
            ]
        )
        return command

    def _dependency_update_required(self, service_name, repository_path):
        """Check whether helm charts' dependencies need to be updated."""
        process = self._execute(["helm", "dep", "list", service_name], cwd=repository_path)
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

    def _check_helm_dependencies(self, deck, temp_dir):
        """Update helm charts' dependencies if needed."""
        if self._dependency_update_required(deck.title, temp_dir):
            if not self._install_dependencies(deck.title, temp_dir):
                raise HelmDependencyError(f"could not build dependencies for {deck.title}")
        else:
            logger.debug("dep update not required")

    def _install_dependencies(self, service_name, repository_path):
        """Install dependencies for helm charts."""
        logger.debug(f"helm dep up for {service_name}")
        process = self._execute(["helm", "dep", "up", service_name], cwd=repository_path)
        return process.returncode == 0

    def _execute(self, cmd, cwd, env=None) -> subprocess.Popen:
        """Run a certain command.

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

    def _prepare_gpg(self, sops_env: dict) -> None:
        private_key = sops_env["PGP_PRIVATE_KEY"]
        subprocess.call('echo "{key}" | gpg --fast-import'.format(key=private_key), shell=True)
