"""The catalog group of the ArcPy `TableOps`: `exists`, `data_type_of`, `create_workspace`.

How: `exists` is the engine's own presence call under the guard, since the engine answers
it for every catalog kind, a workspace included, where Describe fails on a missing path.
`data_type_of` reads presence first and then one Describe for the kind, through the
schema module's reader, so a missing path is a contract error and not an engine failure.
`create_workspace` refuses a path that does not end in the format's suffix and a path
something is already at before any tool runs, because the session applies the project
environment standard with overwrite on and the tool would otherwise replace what is
there; then it dispatches through `CREATORS`, one creator per format, which hands the
engine the folder and the stem since the engine appends the suffix itself. A parent the
engine cannot create into is the engine's own failure, which `run_tool` wraps as
`EngineError` naming the tool. ADR-0018 AR-D23, ADR-0019 PC-D31, PC-D32.
"""

from __future__ import annotations

import os
from collections.abc import Callable, Mapping
from types import MappingProxyType

from ag.adapters.arcpy._base import ArcpyPortBase
from ag.adapters.arcpy.session import ArcpySession
from ag.adapters.arcpy.support.dataset_schema import data_type
from ag.adapters.arcpy.support.dataset_writer import split_path
from ag.core.errors import ErrorContext
from ag.core.handles import ScratchHandle
from ag.core.types import DataType
from ag.ports.errors import PortContractError
from ag.ports.workspace_format import WorkspaceFormat

FILE_GDB_TOOL = "management.CreateFileGDB"
"""The engine's tool for a file geodatabase; takes the folder and the name, and appends
the suffix to a name without one."""


class Catalog(ArcpyPortBase):
    """The catalog methods of `TableOps`, through the session."""

    def exists(self, *, input: ScratchHandle) -> bool:
        """Whether anything is at `input`'s path."""
        return _exists(self._session, os.fspath(input))

    def data_type_of(self, *, input: ScratchHandle) -> DataType:
        """The kind at `input`'s path; a missing path or any kind but a table or a
        feature class is a contract error."""
        path = os.fspath(input)
        if not _exists(self._session, path):
            raise PortContractError(
                f"{input!r} names nothing: there is nothing at {path!r}, and the kind "
                "of a dataset is asked after its presence.",
                context=ErrorContext(handle=path),
            )
        return data_type(self._session, path)

    def create_workspace(self, *, path: str, fmt: WorkspaceFormat) -> None:
        """One empty workspace at `path` in the format `fmt`, refused before any tool
        when the suffix is wrong or something is at the path already."""
        if not path.endswith(fmt.suffix):
            raise PortContractError(
                f"{path!r} does not end in {fmt.suffix!r}, the suffix of a "
                f"{fmt.name} workspace; the caller names the full path as the format "
                "spells it.",
                context=ErrorContext(handle=path),
            )
        if _exists(self._session, path):
            raise PortContractError(
                f"{path!r} is already there; a workspace is created once, and the "
                "session's overwrite setting would otherwise empty it.",
                context=ErrorContext(handle=path),
            )
        CREATORS[fmt](self._session, path)


def _exists(session: ArcpySession, path: str, /) -> bool:
    """The engine's presence answer for `path`, under the guard."""
    with session.guard("Exists"):
        import arcpy

        return arcpy.Exists(path)


def _create_file_gdb(session: ArcpySession, path: str, /) -> None:
    """A file geodatabase at `path`: the tool takes the folder and the stem."""
    folder, name = split_path(path)
    stem = name.removesuffix(WorkspaceFormat.FILE_GDB.suffix)
    session.run_tool(FILE_GDB_TOOL, out_folder_path=folder, out_name=stem)


CREATORS: Mapping[WorkspaceFormat, Callable[[ArcpySession, str], None]] = (
    MappingProxyType({WorkspaceFormat.FILE_GDB: _create_file_gdb})
)
"""The creator of each format this adapter makes, keyed by the port's enum."""
