"""The catalog group of the in-memory `TableOps`: `exists`, `data_type_of`,
`create_workspace`.

Presence and kind come from the store: a dataset's kind is its schema's, a workspace
path is refused as the engine would refuse a kind no port method takes, and a missing
path is a contract error. `create_workspace` records the workspace; a path something is
already at is refused by the store before anything is recorded, and a parent folder that
is missing on the real filesystem is an `EngineError` naming this method as the tool, so
the fake fails where an engine fails and a caller that forgot to make the parent learns
it here and not under the engine. ADR-0019 PC-D31, PC-D32.
"""

from __future__ import annotations

import os

from ag.adapters.fakes.memory._base import MemoryPortBase
from ag.core.errors import ErrorContext
from ag.core.handles import ScratchHandle
from ag.core.types import DataType
from ag.ports.errors import EngineError, PortContractError
from ag.ports.table_ops import TableOps
from ag.ports.workspace_format import WorkspaceFormat

WORKSPACE_TOOL = TableOps.create_workspace.__name__
"""What the in-memory adapter names as the tool when a workspace cannot be created: it
runs no engine tool, so the port method is the tool."""


class Catalog(MemoryPortBase):
    """The catalog methods of `TableOps`, over the store."""

    def exists(self, *, input: ScratchHandle) -> bool:
        """Whether a dataset or a workspace is at `input`'s path."""
        return self._store.present(os.fspath(input))

    def data_type_of(self, *, input: ScratchHandle) -> DataType:
        """The kind at `input`'s path; a workspace or a missing path is a contract
        error."""
        path = os.fspath(input)
        if self._store.is_workspace(path):
            raise PortContractError(
                f"{input!r} names a workspace at {path!r}, which no port method takes "
                "as a dataset.",
                context=ErrorContext(handle=path),
            )
        return self._store.read(input).schema.data_type

    def create_workspace(self, *, path: str, fmt: WorkspaceFormat) -> None:
        """Records an empty workspace at `path`: a path something is already at is the
        store's contract error, and only a new path is held to having a parent."""
        if not self._store.present(path):
            _refuse_missing_parent(path)
        self._store.record_workspace(path, fmt=fmt)


def _refuse_missing_parent(path: str, /) -> None:
    """An `EngineError` naming this adapter's tool when `path`'s parent folder is not
    a directory on the real filesystem, where an engine would fail to create into it."""
    parent = os.path.dirname(path)
    if not os.path.isdir(parent):
        raise EngineError(
            f"{WORKSPACE_TOOL} failed: {parent!r} is not a directory, so nothing can be "
            f"created at {path!r}.",
            context=ErrorContext(
                handle=path,
                tool=WORKSPACE_TOOL,
                tool_messages=(f"{parent!r} is not a directory",),
            ),
        )
