"""A real session and a fresh file geodatabase per engine test.

What: `Pro`, the session on the engine, the test's workspace, and the builders behind
one object, so a test names what it does and not where the helper lives; `pro`, the
fixture that opens the session and creates the workspace under `tmp_path`.

How: the builders are imported inside the fixture and the methods, never at module
level, since collection imports this module where there is no ArcPy. The session is
opened per test, so every test starts from the environment standard freshly applied.
"""

from __future__ import annotations

from contextlib import AbstractContextManager
from dataclasses import dataclass
from pathlib import Path

import pytest

from ag.adapters.arcpy.session import ArcpySession, open_session
from ag.core.handles import ScratchHandle
from ag.core.types import DataType
from tests.support.cases import DatasetCase, Seeded


@dataclass(frozen=True)
class Pro:
    """The engine, the workspace and the builders, for one test."""

    session: ArcpySession
    workspace: str

    def path(self, name: str, *, workspace: str | None = None) -> str:
        return f"{self.workspace if workspace is None else workspace}/{name}"

    def handle(
        self,
        name: str,
        data_type: DataType = DataType.FEATURE_CLASS,
        *,
        workspace: str | None = None,
    ) -> ScratchHandle:
        from tests.support.gdb_cases import handle_at

        return handle_at(
            self.workspace if workspace is None else workspace, name, data_type
        )

    def seed(self, case: DatasetCase, *, workspace: str | None = None) -> Seeded:
        from tests.support.gdb_cases import seed_case

        return seed_case(
            self.session,
            workspace=self.workspace if workspace is None else workspace,
            case=case,
        )

    def read_cells(
        self, *, path: str, tokens: tuple[str, ...], where: str | None = None
    ) -> list[tuple[object, ...]]:
        from tests.support.arcpy import gdb

        return gdb.read_cells(self.session, path=path, tokens=tokens, where=where)

    def hold_cursor(self, *, path: str) -> AbstractContextManager[None]:
        from tests.support.arcpy import gdb

        return gdb.hold_cursor(self.session, path=path)


@pytest.fixture
def pro(tmp_path: Path) -> Pro:
    """The engine with a fresh file geodatabase; for marked tests only."""
    from tests.support.arcpy import gdb

    session = open_session()
    workspace = gdb.file_gdb(session, directory=str(tmp_path), name="engine")
    return Pro(session=session, workspace=workspace)
