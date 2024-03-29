import logging
import os
import subprocess
import tempfile

from commons.helm import utils
from commons.helm.data_classes import DeckData, RenderEnvironment, SopsProviderType
from commons.helm.exceptions import HelmChartRenderError, HelmDependencyError

logger = logging.getLogger("projects.helm")


class HelmCharts:
    """Renders helm charts and provides path to rendered output.

    Can be used as a context manager:
    with HelmCharts(repository_directory, deck) as dir:
        for root, dirs, files in os.walk(dir):
            ...
    """

    def __init__(self, repository_directory, deck: DeckData, environment: RenderEnvironment):
        self.repository_directory = repository_directory
        self.deck = deck
        self.environment = environment
        self.values_path = environment.values_path

    def __enter__(self):
        # check dependencies
        directory = os.path.join(self.repository_directory, self.deck.dir_path)
        utils.check_helm_dependencies(directory)

        # create tempdir for output
        self.rendered_chart_dir = tempfile.TemporaryDirectory()
        logger.debug("created temporary directory:" + str(self.rendered_chart_dir.name))

        # generate command and env
        output_dir = self.rendered_chart_dir.name
        # deck.values starts with /. That needs to be excluded.
        values = os.path.join(self.repository_directory, self.values_path.lstrip("/"))
        name = utils.slugify(self.deck.title)
        chart = os.path.join(".", self.deck.dir_path)
        parameters = utils.get_additional_render_parameters(self.deck, self.environment)
        command = utils.get_command(output_dir, values, name, chart, *parameters, secrets=bool(self.deck.sops))
        env = self._get_env()

        # execute command
        logger.debug(f"running: {command}, in dir {self.repository_directory}")
        process = utils.execute(command, cwd=self.repository_directory, env=env)
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

    def _prepare_gpg(self, sops_env: dict) -> None:
        private_key = sops_env["PGP_PRIVATE_KEY"]
        subprocess.call('echo "{key}" | gpg --fast-import'.format(key=private_key), shell=True)
