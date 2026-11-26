"""What the scratch manager expects of the engine beyond the conformance cases: every
workspace it names is created as a workspace through `ArcpyTableOps`, with the
loose-files directory beside the stage workspace; and the engine's internal file names
in a fresh geodatabase fit the length `staging/workspace.py` declares, so an engine
upgrade that adds a longer system file fails here and not on a person's machine (A34).
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from ag.adapters.arcpy.table_ops import ArcpyTableOps
from ag.core.types import PodRole
from ag.staging.scratch import ScratchFileManager
from ag.staging.workspace import INTERNAL_FILE_NAME_LENGTH
from tests.engine.arcpy.conftest import Pro
from tests.support.arcpy import gdb
from tests.support.cases import lookup, roads

pytestmark = pytest.mark.arcpy

STAGE = "n100/road/thin_roads"
"""A stage's qualified name, as T2.13 shapes it; opaque to the manager."""

CALLS = (f"{STAGE}:dissolve", f"{STAGE}:dissolve_2")
"""Call identities carrying the stage and the operation; the two separators the
rendering must keep out of a path."""


def test_create_workspaces_creates_every_workspace_and_the_loose_files_directory(
    pro: Pro, tmp_path: Path
) -> None:
    root = tmp_path / "scratch"
    root.mkdir()
    manager = ScratchFileManager(
        root=str(root),
        stage=STAGE,
        calls=CALLS,
        role=PodRole.POD,
        partition_index=3,
        table=ArcpyTableOps(session=pro.session),
    )
    manager.create_workspaces()
    workspaces = (
        manager.stage_workspace(),
        *(manager.operation_workspace(call) for call in CALLS),
    )
    assert all(gdb.is_workspace(pro.session, path=path) for path in workspaces)
    assert os.path.isdir(manager.loose_files())


def test_the_engines_internal_file_names_fit_the_declared_length(pro: Pro) -> None:
    pro.seed(roads())
    pro.seed(lookup())
    longest = max(len(entry.name) for entry in os.scandir(pro.workspace))
    assert longest <= INTERNAL_FILE_NAME_LENGTH
