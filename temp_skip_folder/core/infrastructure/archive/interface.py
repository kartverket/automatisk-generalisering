from __future__ import annotations

from abc import ABC, abstractmethod

from composition_configs.logic_config import DataRef


class ArchiveClient(ABC):
    @abstractmethod
    def read(self, remote: DataRef) -> DataRef:
        """Read remote input and return local DataRef path."""

    @abstractmethod
    def write(self, local: DataRef, remote: DataRef) -> None:
        """Write local output to remote destination."""

    @abstractmethod
    def list_objects(self, path: str) -> list[str]:
        """List objects under a backend-specific path."""

    @abstractmethod
    def get_object(self, path: str) -> bytes:
        """Fetch object bytes from a backend-specific path."""

    @abstractmethod
    def put_object(self, path: str, data: bytes) -> None:
        """Write object bytes to a backend-specific path."""

    @abstractmethod
    def delete_object(self, path: str) -> None:
        """Delete an object by backend-specific path."""
