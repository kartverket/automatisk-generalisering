"""TEMPLATE — not shipped. Target module: `src/ag/staging/workspace.py`.

Workspace format: the join rule, name legality, and the name budget.

A `.gdb` is a directory holding feature classes; a `.gpkg` is a single SQLite file
holding tables; a plain directory holds `.shp` files. All three are "a workspace with
named layers inside", which is why the model says workspace rather than directory —
and why `container` is reserved for OCI (01-terminology §3).

THE ONLY PLACE THE FORMAT IS KNOWN. ScratchFileManager holds the pod's paths but asks
this module how to spell them, so an operation never learns which format is in use and
a `.gpkg` future is one enum member plus two branches.
"""

from __future__ import annotations

import posixpath
from collections.abc import Sequence
from enum import Enum

from ag.core.types import DataType


class WorkspaceFormat(Enum):
    """How named layers are held. See the module docstring."""

    FILE_GDB = "gdb"
    GEOPACKAGE = "gpkg"
    DIRECTORY = "dir"


# ---------------------------------------------------------------------------
# Name budget
# ---------------------------------------------------------------------------

GDB_LAYER_NAME_LIMIT = 160
"""File geodatabase feature class / table name limit."""

WINDOWS_MAX_PATH = 260
"""Full-path limit on Windows without long-path support. Does not exist on Linux,
where filenames cap at 255 bytes and paths at 4096."""


def name_budget(workspace: str, windows: bool) -> int:
    """How many characters a layer name may use.

    WHICH LIMIT BINDS:

      - On the PODS (Linux): only GDB_LAYER_NAME_LIMIT. MAX_PATH does not exist
        there, and 255-byte filenames are never the constraint.
      - On Windows with a SHALLOW root (C:\\tmp\\...gdb, ~55 chars): budget is
        min(160, 260 - 55 - 1) = 160, so the GDB limit still binds first.
      - On Windows with a DEEP dev root (C:\\Users\\...\\output\\gis_files\\n100\\...,
        120+ chars): MAX_PATH binds first and the budget drops below 160.

    Computing it rather than hardcoding 160 is what turns a mysterious arcpy failure
    on a developer's machine into a clear message naming the limit that was hit.
    """
    if not windows:
        return GDB_LAYER_NAME_LIMIT
    return min(GDB_LAYER_NAME_LIMIT, WINDOWS_MAX_PATH - len(workspace) - 1)


TRAIL_SEPARATOR = "__"


def render_trail(trail: Sequence[str], leaf: str, budget: int) -> str:
    """Render a scope trail plus a leaf name into one legal layer name.

    THE ONE PLACE THIS HAPPENS, which is the whole preparation needed for deep
    nesting later. Today it joins. When trails start exceeding the budget, this
    becomes first-two + hash + last-two and NOTHING ELSE IN THE SYSTEM CHANGES:

        stage_a__op_b__t7f3a91c2__tool_y__merged

    The `t` + 8 hex marker is legal in the FC charset (alphanumeric and underscore
    only - `~` and `-` are not), greppable, and obviously not a real label. The hash
    is computed over the FULL trail, and ScratchFileManager.manifest() maps every
    rendered name back to its complete trail, so a truncated name is always
    untanglable rather than merely hashed.

    Measured against the real codebase, four levels is the realistic depth:
    `gangsykkel_dissolver__eliminate_small_polygons__partition_iterator__merged` is
    74 characters. Five is about 110. So this is preparation, not a current need -
    which is why it errors rather than eliding.
    """
    rendered = TRAIL_SEPARATOR.join((*trail, leaf))
    if len(rendered) <= budget:
        return rendered
    raise ValueError(
        f"scratch name {rendered!r} is {len(rendered)} characters, over the "
        f"{budget} available. Shorten a scope label, or implement trail elision "
        "here - see this function's docstring. Truncating silently would make two "
        "distinct files collide."
    )


def normalize_layer_name(name: str) -> str:
    """File GDB names must start with a letter or underscore and contain only
    alphanumerics and underscore. Enforced in ONE place rather than discovered per
    tool."""
    raise NotImplementedError(
        "reject or rewrite illegal characters; reject leading digits and reserved "
        "words. Reject rather than rewrite where possible - a silently rewritten "
        "name is a name the developer cannot grep for."
    )


# ---------------------------------------------------------------------------
# The join rule
#
# Lifted off ScratchFileManager so the format lives in one module rather than in
# three methods of a class whose subject is paths, not formats.
# ---------------------------------------------------------------------------


def workspace_path(root: str, stem: str, fmt: WorkspaceFormat) -> str:
    """Where one workspace sits inside the pod scratch root."""
    if fmt is WorkspaceFormat.DIRECTORY:
        return posixpath.join(root, stem)
    return posixpath.join(root, f"{stem}.{fmt.value}")


def join(workspace: str, layer: str, data_type: DataType, fmt: WorkspaceFormat) -> str:
    """The format join rule. The only place it lives."""
    if fmt is WorkspaceFormat.DIRECTORY:
        suffix = ".dbf" if data_type is DataType.TABLE else ".shp"
        return posixpath.join(workspace, f"{layer}{suffix}")
    return posixpath.join(workspace, layer)


def sidecar(workspace: str) -> str:
    """The directory beside a workspace, for files a gdb cannot hold - .lyrx, .csv,
    logs, .prj."""
    base, _, _ = workspace.rpartition(".")
    return base or workspace
