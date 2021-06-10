import hashlib
import logging
import tempfile
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from functools import cached_property
from typing import List

from git import GitCommandError, Repo

from commons.helm.exceptions import RepositoryAuthenticationFailed, RepositoryBranchUnavailable, RepositoryCloningFailed


@dataclass
class FileInformation:
    path: str
    encrypted: bool
    providers: List

    def to_json(self):
        return {"path": self.path, "encrypted": self.encrypted, "providers": self.providers}


@dataclass
class Repository:
    url: str
    username: str = None
    token: str = None
    branch: str = None

    @property
    def repo_url(self):
        return self.parse_url(self.url, username=self.username, token=self.token, branch=self.branch)

    def __enter__(self):
        logger = logging.getLogger("projects.helm")
        self.temp_dir = tempfile.TemporaryDirectory()
        logger.debug(f"start cloning repo to: {self.temp_dir} for {self.repo_url}")
        try:
            return Repo.clone_from(self.repo_url, self.temp_dir.name, depth=1, branch=self.branch)
        except GitCommandError as e:
            if f"fatal: Remote branch {self.branch} not found in upstream origin" in e.stderr:
                raise RepositoryBranchUnavailable
            elif "fatal: Authentication failed" in e.stderr:
                raise RepositoryAuthenticationFailed
            else:
                raise RepositoryCloningFailed

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.temp_dir.cleanup()

    @staticmethod
    def parse_url(url, username=None, token=None, branch="master"):
        protocol = url.split("//")[0]
        uri = url.split("//")[1]
        if username and token:
            return f"{protocol}//{username}:{token}@{uri}"
        else:
            return f"{protocol}//{uri}"


@dataclass
class RepositoryData:
    current_commit: str
    current_commit_date_time: datetime


class SopsProviderType(Enum):
    AWS = "aws"
    PGP = "pgp"
    GCP = "gcp"


@dataclass
class SopsProvider:
    type: SopsProviderType

    def get_env(self):
        return {}


@dataclass
class AWSKMS(SopsProvider):
    access_key: str
    secret_access_key: str

    def get_env(self):
        return {
            "AWS_SDK_LOAD_CONFIG": 1,
            "AWS_ACCESS_KEY_ID": self.access_key,
            "AWS_SECRET_ACCESS_KEY": self.secret_access_key,
        }


@dataclass
class PGPKey(SopsProvider):
    private_key: str

    def get_env(self):
        return {"PGP_PRIVATE_KEY": self.private_key}


@dataclass
class SpecsData:
    name: str
    source: str
    content: str
    kind: str


@dataclass
class RenderEnvironment:
    specs_data: List[SpecsData]
    values_path: str = ""


@dataclass
class DeckData:
    title: str
    description: str
    type: str
    dir_path: str
    file_information: dict
    environments: List[RenderEnvironment]
    sops: SopsProvider = None
    namespace: str = ""

    @cached_property
    def hash(self):
        deck_hash = hashlib.sha256()
        deck_hash.update(f"{self.title}{self.type}".encode("utf-8"))
        return deck_hash.hexdigest()
