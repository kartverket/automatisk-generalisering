"""Workspace naming: the format, the join rule, name legality and the limits every name
the scratch manager writes must meet.

What: `FORMAT`, the one format a pod's workspaces take; `legal_name`, the characters a
name may use; `render_trail`, a scope trail and leaf as one layer name; `render_identity`,
a stage or call identity as a path-safe stem; `workspace_path`, `loose_files_path` and
`join`, the three spellings of a path under the scratch root; and the limits, each
declared once with its evidence beside it.

How: every name passes one of two join points, `workspace_path` for a workspace stem and
`join` for a layer, and each checks legality there. A workspace name has one bound,
`WORKSPACE_NAME_LIMIT`: what leaves a geodatabase's longest internal file within the
Windows file-path limit under the root allowance. That bound is below the Windows folder
limit less the allowance and below the Linux name limit, which
`tests/unit/staging/test_workspace.py` pins, so no second check is needed. The loose-files
directory is the workspace path without its suffix, so the same bound covers it and leaves
a loose file `LOOSE_FILE_NAME_ROOM` characters. A layer name is bounded by the
geodatabase's own limit and by nothing else: Pro on Windows created, listed and opened
layers whose catalog paths were 300 characters, so a layer name counts toward no path
limit. A name over a limit raises; nothing is truncated, because a truncated name can
collide with another.

Why: pod output must open on Windows without an exporter (A34). The system runs only in
the Linux image (ADR-0018 Direction 6), but a person opens a scratch dump or a transfer
directory on Windows, where the tools that copy and extract files stop at `MAX_PATH`
while the engine's own file layer does not. The limits are measured, not assumed: the
rows cited beside each constant are in
`docs/refactor/temp/findings/slice_1c_scratch_manager_evidence.md`. The per-file check
on a loose file, its path from the scratch root against `WINDOWS_FILE_PATH_LIMIT` less the
allowance, lands with the first method that hands out such a path (T2.13).
"""

from __future__ import annotations

import posixpath
import re
from collections.abc import Sequence

from ag.core.errors import ErrorContext
from ag.ports.workspace_format import WorkspaceFormat
from ag.staging.errors import WorkspaceError

FORMAT = WorkspaceFormat.FILE_GDB
"""The format of every workspace under a scratch root. The join rule here is its own."""

LAYER_NAME_LIMIT = 160
"""The file geodatabase's layer-name limit: a feature class and a table alike are created
at 160 characters and refused at 161 with the engine's error 160331 (evidence rows a2,
a3)."""

WORKSPACE_NAME_BYTES = 255
"""The filesystem's limit on one name on Linux, in bytes, where the pods run (evidence
row d)."""

WINDOWS_FILE_PATH_LIMIT = 259
"""The longest file path the tools a person copies and extracts with create on Windows
without long-path support: `MAX_PATH` less the terminator (A34; evidence row 1b)."""

WINDOWS_FOLDER_PATH_LIMIT = 247
"""The longest folder path the same tools create; the margin below the file limit is what
a short file name inside the folder needs (A34; evidence row 1b)."""

WINDOWS_ROOT_ALLOWANCE = 100
"""Characters reserved above the scratch root for where a person unpacks a dump on
Windows: about forty for the folder and about sixty for the dump's own structure (A34)."""

INTERNAL_FILE_NAME_LENGTH = 48
"""The longest file name inside a file geodatabase, which the engine's system tables add
to an empty one (evidence rows e, 2b). `tests/engine/arcpy/test_scratch.py` reads it on
the engine, so an upgrade that adds a longer name fails there and not on a person's
machine."""

WORKSPACE_NAME_LIMIT = (
    WINDOWS_FILE_PATH_LIMIT - WINDOWS_ROOT_ALLOWANCE - 1 - INTERNAL_FILE_NAME_LENGTH
)
"""The longest workspace name, suffix included: a geodatabase's longest internal file
still fits a Windows file path under the allowance. The one check a workspace name needs;
see the module docstring."""

LOOSE_FILE_NAME_ROOM = (
    WINDOWS_FILE_PATH_LIMIT
    - WINDOWS_ROOT_ALLOWANCE
    - 1
    - (WORKSPACE_NAME_LIMIT - len(FORMAT.suffix))
)
"""What a file in the loose-files directory may be named when that directory's name is
at its longest; the method that hands out loose-file paths checks each against it."""

LAYER_SEPARATOR = "__"
"""Joins a trail's segments into a layer name. A segment holds single underscores only
(`core/handles.py`), so the join reads back unambiguously."""

_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
"""ASCII letters, digits and underscores, a letter or underscore first: what the file
geodatabase accepts and every filesystem spells alike."""

_UNSAFE = re.compile(r"[^A-Za-z0-9_]")
"""What `render_identity` replaces: everything `_NAME` does not admit inside a name."""


def legal_name(name: str, /) -> str:
    """`name` when it matches `_NAME`; otherwise a `WorkspaceError`. Rejects and never
    rewrites, since a rewritten name is one nobody can grep for (evidence row b)."""
    if _NAME.fullmatch(name) is None:
        raise WorkspaceError(
            f"name {name!r} is not ASCII letters, digits and underscores starting with "
            "a letter or underscore, which every workspace, layer and loose file needs "
            "to open on Linux and on Windows.",
            context=ErrorContext(handle=name),
        )
    return name


def render_trail(trail: Sequence[str], leaf: str) -> str:
    """A scope trail and its leaf as one layer name, within `LAYER_NAME_LIMIT`."""
    rendered = LAYER_SEPARATOR.join((*trail, leaf))
    if len(rendered) > LAYER_NAME_LIMIT:
        raise WorkspaceError(
            f"layer name {rendered!r} is {len(rendered)} characters, over the "
            f"geodatabase's {LAYER_NAME_LIMIT}. Shorten a scope label or the leaf; "
            "truncating would let two distinct names collide.",
            context=ErrorContext(handle=rendered),
        )
    return rendered


def render_identity(identity: str, /) -> str:
    """A stage or call identity as a stem: every character outside ASCII letters, digits
    and underscore becomes an underscore, so no separator of the identity reaches a path.
    Not one-to-one; the manager refuses two identities that render alike."""
    return _UNSAFE.sub("_", identity)


def workspace_path(root: str, stem: str) -> str:
    """Where the workspace named `stem` sits under `root`, suffix added; the name is
    checked for legality and against `WORKSPACE_NAME_LIMIT`."""
    name = legal_name(stem) + FORMAT.suffix
    if len(name) > WORKSPACE_NAME_LIMIT:
        raise WorkspaceError(
            f"workspace name {name!r} is {len(name)} characters, over "
            f"{WORKSPACE_NAME_LIMIT}: its internal files would not fit a Windows path "
            f"of {WINDOWS_FILE_PATH_LIMIT} under a root of {WINDOWS_ROOT_ALLOWANCE}.",
            context=ErrorContext(handle=name),
        )
    return posixpath.join(root, name)


def loose_files_path(workspace: str, /) -> str:
    """The directory beside `workspace` for files a geodatabase cannot hold: the
    workspace path without its suffix, so it is bounded by the same check."""
    return workspace.removesuffix(FORMAT.suffix)


def join(workspace: str, layer: str) -> str:
    """The path of `layer` inside `workspace`: the format's join rule, and the one
    place a layer name is checked for legality."""
    return posixpath.join(workspace, legal_name(layer))
