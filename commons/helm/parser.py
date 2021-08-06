import logging
import os
import re
from datetime import datetime
from typing import List, Tuple

import yaml
from yaml import MarkedYAMLError

from commons.helm.context_manager import HelmCharts
from commons.helm.data_classes import (
    DeckData,
    FileInformation,
    RenderEnvironment,
    Repository,
    RepositoryData,
    SpecsData,
)

logger = logging.getLogger("projects.helm")


class ChartYamlParser:
    def __init__(self, temporary_directory):
        self.temporary_directory = temporary_directory

    def parse(self, dir_path, fname):
        return self._read_deck_data(fname, dir_path)

    def _read_deck_data(self, file_path, dir_path) -> DeckData:
        """Retrieves deck information for a given Chart.yaml found in the temporary directory under `file_path`."""
        if os.path.isfile(file_path):
            with open(file_path) as fchart:
                chart = yaml.load(fchart, Loader=yaml.FullLoader)
                service_name = chart.get("name", "<name not set>")
                service_description = chart.get("description", "<description not set>")
                service_type = chart.get("type", "")
                return DeckData(
                    title=service_name,
                    type=service_type,
                    description=service_description,
                    dir_path=dir_path,
                    file_information=self._retrieve_file_information(os.path.dirname(file_path)),
                    environments=[],
                )

    def _retrieve_file_information(self, dir_path):
        """Retrieves the directory and file structure of deck.

        This is needed to display the files and directories in the frontend (for Helm value selection).
        """
        result = []
        for tmp_dir_path, tmp_dirs, tmp_files in os.walk(dir_path):
            # Directories may contain multiple files.
            # TODO handle directories with a more detailed approach ...
            # ... (parse files and provide general information for dir)
            result.append(
                FileInformation(
                    path=tmp_dir_path[len(self.temporary_directory) :], encrypted=False, providers=[]
                ).to_json()
            )
            tmp_yaml_files = filter(lambda x: x.endswith("yaml"), tmp_files)
            for tmp_file in tmp_yaml_files:
                file_information = self._get_file_information(tmp_dir_path, tmp_file)
                result.append(file_information.to_json())
        return {"information": result}

    def _get_file_information(self, file_path, file_name) -> FileInformation:
        """Retrieves basic information about a file.

        returns: FileInformation

        We assume that any given `file_path` + `file_name` is a path to a YAML file. Checks whether a file is
        encrypted or not. If it is encrypted the type of provider is stored on the FileInformation object.
        """

        with open(os.path.join(file_path, file_name), "r") as file:
            short_path = os.path.join(file_path[len(self.temporary_directory) :], file_name)
            try:
                yaml_file = yaml.load(file, Loader=yaml.FullLoader)
            except MarkedYAMLError:
                return FileInformation(path=short_path, encrypted=False, providers=[])
            sops = yaml_file.get("sops", False)
            encrypted = bool(sops)
            providers = []
            if encrypted:
                for provider in ["kms", "gcp_kms", "pgp"]:
                    if bool(sops.get(provider)):
                        providers.append(provider)
            return FileInformation(path=short_path, providers=providers, encrypted=encrypted)


class SpecsParser:
    @classmethod
    def read_specs(cls, path):
        """Parse given file for specs.

        :returns List[SpecsData]
        """
        with open(path, "r") as f:
            specs = []
            # logger.debug(f"reading file: {filename}")
            content = f.read()
            # one file can consist of multiple specs
            for spec in content.split("---"):
                # check if this is rather empty
                if not spec.strip():
                    continue
                # we parse the file in order to extract the required information
                kind_re = r"kind:\s*\w+"
                source_re = r"Source:\s*[\w/\-\.]*"
                kindmatch = re.search(kind_re, spec)
                if kindmatch:
                    kind = kindmatch.group().split(":")[-1].strip()
                else:
                    kind = None
                sourcematch = re.search(source_re, spec)
                if sourcematch:
                    source = sourcematch.group().split(":")[-1].strip()
                else:
                    # we take the source from the last
                    pass
                specs.append(
                    SpecsData(
                        name=os.path.basename(path),
                        source=source,
                        content=spec,
                        kind=kind,
                    )
                )

        return specs


class HelmRepositoryParser:
    def __init__(self, repository_url, access_username=None, access_token=None, branch="master"):
        """Initializes the parser for a given repository."""
        self.url = repository_url
        self.username = access_username
        self.token = access_token
        self.branch = branch
        self._repository_data: RepositoryData = None
        self._deck_data: List[DeckData] = []

    @property
    def repository_data(self):
        return self._repository_data

    @property
    def deck_data(self):
        return self._deck_data

    def get_repository_data(self):
        return self.repository_data

    def get_deck_data(self):
        return self.deck_data

    def parse(self):
        """Clones repository and parses repository meta information as well as deck information."""
        with Repository(self.url, self.username, self.token, self.branch) as repo:
            self._repository_data = RepositoryData(
                current_commit=repo.head.commit,
                current_commit_date_time=datetime.fromtimestamp(repo.head.commit.committed_date),
            )
            self.parse_deck_data(repo.working_dir)

    def render(self, *args: Tuple[DeckData, RenderEnvironment]):
        result = []
        with Repository(self.url, self.username, self.token, self.branch) as repo:
            self._repository_data = RepositoryData(
                current_commit=repo.head.commit,
                current_commit_date_time=datetime.fromtimestamp(repo.head.commit.committed_date),
            )
            if not self.deck_data:
                self.parse_deck_data(repo.working_dir)
            for deck, environment in args:
                specs = self.read_specs_data(repo.working_dir, deck, environment)
                environment.specs_data = specs
                result.append((deck, environment))
        return result

    def read_specs_data(self, temp_dir: str, deck: DeckData, environment: RenderEnvironment):
        result = []
        with HelmCharts(repository_directory=temp_dir, deck=deck, environment=environment) as kube_files_dir:
            for root, dirs, files in os.walk(kube_files_dir):
                for fname in filter(lambda fname: fname.endswith(".yaml"), files):
                    specs = SpecsParser.read_specs(os.path.join(root, fname))
                    result.extend(specs)
        return result

    def parse_deck_data(self, temp_dir):
        """Iterates through repository structure and triggers Chart.yaml file parsing."""
        for dir_path, dirs, files in os.walk(temp_dir):
            chart_files = list(filter(lambda x: x == "Chart.yaml" or x == "chart.yaml", files))
            if chart_files:
                f_path = os.path.join(dir_path, chart_files[0])
                deck_data = ChartYamlParser(temp_dir).parse(os.path.relpath(dir_path, temp_dir), f_path)
                self.deck_data.append(deck_data)
                dirs[:] = []  # don't look for any yaml files in sub directories

    def get_specs(self, deck_hash, environment, sops=None):
        with Repository(self.url, self.username, self.token, self.branch) as repo:
            self._repository_data = RepositoryData(
                current_commit=repo.head.commit,
                current_commit_date_time=datetime.fromtimestamp(repo.head.commit.committed_date),
            )
            self.parse_deck_data(repo.working_dir)
            deck = next(filter(lambda x: deck_hash == x.hash, self.deck_data))
            if sops:
                deck.sops = sops
            return self.read_specs_data(repo.working_dir, deck, environment)
