from __future__ import annotations

import os

from .gcs_client import GcsArchiveClient
from .interface import ArchiveClient
from .local_client import LocalArchiveClient
from .scality_client import ScalityArchiveClient
from .validators import validate_environment


def create_archive_client(environment: str) -> ArchiveClient:
    validate_environment(environment)

    local_client = LocalArchiveClient()

    if environment == "on_cloud":
        return GcsArchiveClient(local_client=local_client)

    endpoint_url = _required_env("SCALITY_ENDPOINT")
    access_key = _required_env("scality_user")
    secret_key = _required_env("scality_pass")
    return ScalityArchiveClient(
        endpoint_url=endpoint_url,
        access_key=access_key,
        secret_key=secret_key,
        local_client=local_client,
    )


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value
