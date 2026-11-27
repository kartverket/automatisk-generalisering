"""By-hand probe for the name limits the scratch manager will enforce: what the engine
does with a layer name at and over the file geodatabase limit, with the characters the
name legality check would refuse or admit, with two names that differ only in case, and
with a geodatabase directory name at the filesystem's name limit.

Run inside the ArcPy image from the repository root, as a module, with `src` and the
root on the path and no dev tools, since the engine writes into `__main__` on import:

    docker run --rm -v "$PWD":/work:ro -w /work \\
      -e PYTHONPATH=/work/src:/work -e PYTHONDONTWRITEBYTECODE=1 \\
      ghcr.io/kartverket/arcpy-linux:12.1 \\
      python -m docs.refactor.temp.slice_1c_name_limits_probe

What it does, on synthetic names and empty datasets under a temporary directory. Every
row prints a case id, the requested name and its length, the outcome (`created`, or the
exception class, the engine's own class when the session wrapped it, and the first line
of the message), whether `Exists` answers for the requested path afterwards, and the
names that appeared in the geodatabase's listing after the attempt, so a name the engine
truncated or rewrote shows up as a different name than the one requested, which is the
only case in which the listed name is printed.

a. Layer name length: a feature class and a table at 159, 160, 161 and 200 characters,
   all in one fresh file geodatabase.
b. Characters: a table under a name starting with a digit, with an underscore and with a
   letter; names holding a hyphen, one of the letters æ, ø and å, and a double
   underscore. Each row also prints what `ValidateTableName` returns for the name in
   that geodatabase.
c. Case: a table `Roads` holding a marker field, then a table `roads` without it, with
   the overwrite setting as the session applied it. Whether the second is refused,
   overwrites the first or coexists with it is read from the outcome, the listing, and
   whether the marker field is still on `Roads`.
d. Workspace name: file geodatabases whose directory name, `.gdb` included, is 250, 255
   and 256 bytes, each under the temporary directory.
e. Internal file names: in a fresh geodatabase of its own, the longest file name inside
   the `.gdb` directory, digits masked as `#`, with its length and the file count, when
   the geodatabase is empty, after a feature class, after a table, and after an
   attribute index with a 40-character name on that table. How deep a `.gdb` may sit
   on a system with a path limit is the limit less the longest internal name, so the
   Windows check reads this length at run time and this row records what the names
   look like.

Reserved words are out of scope. Observations only: nothing here asserts, no value of
any row is printed, and the output is pasted into the evidence file. The temporary
directory's path is replaced by `<base>` in every line printed, so no machine path
appears in the paste. Nothing after `open_session` names the `datetime` class, which the
engine rebinds in `__main__`.
"""

from __future__ import annotations

import os
import re
import shutil
import tempfile
from typing import Protocol

from ag.adapters.arcpy.session import ArcpySession, open_session
from ag.adapters.arcpy.support.dataset_writer import add_fields
from ag.adapters.arcpy.table_ops.catalog import FILE_GDB_TOOL
from ag.ports import Field, FieldType
from ag.ports.workspace_format import WorkspaceFormat
from tests.support.arcpy import gdb

SUFFIX = WorkspaceFormat.FILE_GDB.suffix
CRS_CODE = 25833
"""EPSG code of the feature classes created here; only a geometry type and a reference
are needed for an empty feature class, and the value plays no part in what is
observed."""

LENGTHS = (159, 160, 161, 200)
CHARACTER_CASES = (
    ("b1", "2nd"),
    ("b2", "_x"),
    ("b3", "x1"),
    ("b4", "a-b"),
    ("b5", "aæ"),
    ("b6", "aø"),
    ("b7", "aå"),
    ("b8", "a__b"),
)
WORKSPACE_BYTES = (250, 255, 256)

MARKER = Field("marker", FieldType.LONG)
INDEX_NAME = "ix_" + "x" * 37


class Creator(Protocol):
    """One of the two dataset creators below, as `attempt` calls it."""

    def __call__(self, session: ArcpySession, *, workspace: str, name: str) -> None: ...


class Printer:
    """Prints lines with the temporary directory's path replaced by `<base>`."""

    def __init__(self, base: str) -> None:
        self._base = base

    def __call__(self, text: str) -> None:
        print(text.replace(self._base, "<base>"))


def outcome(error: Exception) -> str:
    """The exception class, the engine's own class when the session wrapped it, and the
    first line of the message."""
    cause = error.__cause__
    inner = f" (from {type(cause).__name__})" if cause is not None else ""
    first = str(error).splitlines()[0] if str(error) else ""
    return f"{type(error).__name__}{inner}: {first}"


def listing(session: ArcpySession, workspace: str) -> set[str]:
    """The dataset names the engine lists inside `workspace`, every kind together."""
    names: set[str] = set()
    with session.guard("da.Walk"):
        import arcpy

        for _, _, found in arcpy.da.Walk(workspace, datatype=["FeatureClass", "Table"]):
            names.update(found)
    return names


def exists(session: ArcpySession, path: str) -> object:
    with session.guard("Exists"):
        import arcpy

        try:
            return arcpy.Exists(path)
        except Exception as error:  # noqa: BLE001  a probe reports, it does not handle
            return outcome(error)


def validate(session: ArcpySession, name: str, workspace: str) -> object:
    with session.guard("ValidateTableName"):
        import arcpy

        try:
            return arcpy.ValidateTableName(name, workspace)
        except Exception as error:  # noqa: BLE001
            return outcome(error)


def create_feature_class(session: ArcpySession, *, workspace: str, name: str) -> None:
    with session.guard("SpatialReference"):
        import arcpy

        reference = arcpy.SpatialReference(CRS_CODE)
    session.run_tool(
        "management.CreateFeatureclass",
        out_path=workspace,
        out_name=name,
        geometry_type="POINT",
        spatial_reference=reference,
    )


def create_table(session: ArcpySession, *, workspace: str, name: str) -> None:
    session.run_tool("management.CreateTable", out_path=workspace, out_name=name)


def attempt(
    session: ArcpySession,
    out: Printer,
    *,
    case: str,
    kind: str,
    workspace: str,
    name: str,
    create: Creator,
    extra: str = "",
) -> None:
    """One row: the creation outcome, `Exists` for the requested path, and the names new
    in the listing afterwards, each with its length."""
    before = listing(session, workspace)
    try:
        create(session, workspace=workspace, name=name)
        result = "created"
    except Exception as error:  # noqa: BLE001
        result = outcome(error)
    after = listing(session, workspace)
    new = sorted(after - before)
    back = (
        ", ".join(
            "the requested name" if found == name else f"{found!r} ({len(found)})"
            for found in new
        )
        or "nothing new"
    )
    out(f"{case:3} {kind:14} len={len(name):3} {name!r}")
    out(f"    -> {result}")
    out(f"    Exists(requested) = {exists(session, f'{workspace}/{name}')!r}")
    out(f"    listing gained: {back}{extra}")


def length_cases(session: ArcpySession, out: Printer, workspace: str) -> None:
    for index, length in enumerate(LENGTHS, start=1):
        for kind, create, mark in (
            ("feature class", create_feature_class, "f"),
            ("table", create_table, "t"),
        ):
            stem = f"{mark}{length}_"
            name = stem + "x" * (length - len(stem))
            attempt(
                session,
                out,
                case=f"a{index}{mark}",
                kind=kind,
                workspace=workspace,
                name=name,
                create=create,
            )


def character_cases(session: ArcpySession, out: Printer, workspace: str) -> None:
    for case, name in CHARACTER_CASES:
        valid = validate(session, name, workspace)
        attempt(
            session,
            out,
            case=case,
            kind="table",
            workspace=workspace,
            name=name,
            create=create_table,
            extra=f"; ValidateTableName -> {valid!r}",
        )


def case_cases(session: ArcpySession, out: Printer, workspace: str) -> None:
    out(f"overwriteOutput as applied: {session.read_environment().overwrite_output}")
    attempt(
        session,
        out,
        case="c1",
        kind="table",
        workspace=workspace,
        name="Roads",
        create=create_table,
    )
    add_fields(session, path=f"{workspace}/Roads", fields=(MARKER,))
    attempt(
        session,
        out,
        case="c2",
        kind="table",
        workspace=workspace,
        name="roads",
        create=create_table,
    )
    with session.guard("ListFields"):
        import arcpy

        try:
            fields = [field.name for field in arcpy.ListFields(f"{workspace}/Roads")]
        except Exception as error:  # noqa: BLE001
            fields = [outcome(error)]
    out(f"    fields on 'Roads' afterwards: {fields!r}")
    out(f"    marker still on 'Roads': {MARKER.name in fields}")
    spelled = sorted(n for n in listing(session, workspace) if n.lower() == "roads")
    out(f"    names spelled roads in any case: {spelled!r}")


def workspace_cases(session: ArcpySession, out: Printer, directory: str) -> None:
    for index, size in enumerate(WORKSPACE_BYTES, start=1):
        stem = "w" * (size - len(SUFFIX))
        name = f"{stem}{SUFFIX}"
        path = f"{directory}/{name}"
        out(f"d{index}  directory name: {len(name)} chars, {len(name.encode())} bytes")
        try:
            session.run_tool(FILE_GDB_TOOL, out_folder_path=directory, out_name=stem)
            result = "created"
        except Exception as error:  # noqa: BLE001
            result = outcome(error)
        out(f"    -> {result}")
        out(f"    Exists(path) = {exists(session, path)!r}")
        out(f"    is_workspace(path) = {gdb.is_workspace(session, path=path)!r}")


def longest_internal(workspace: str) -> str:
    """The longest file name inside the geodatabase directory, digits masked, with its
    length and the number of files."""
    names = os.listdir(workspace)
    longest = max(names, key=len)
    masked = re.sub(r"\d", "#", longest)
    return f"{masked!r} ({len(longest)} chars) among {len(names)} files"


def internal_file_cases(session: ArcpySession, out: Printer, directory: str) -> None:
    workspace = gdb.file_gdb(session, directory=directory, name="internal")
    out(f"e1  empty geodatabase:      {longest_internal(workspace)}")
    create_feature_class(session, workspace=workspace, name="fc")
    out(f"e2  after a feature class:  {longest_internal(workspace)}")
    create_table(session, workspace=workspace, name="tbl")
    add_fields(session, path=f"{workspace}/tbl", fields=(MARKER,))
    out(f"e3  after a table:          {longest_internal(workspace)}")
    try:
        session.run_tool(
            "management.AddIndex",
            in_table=f"{workspace}/tbl",
            fields=[MARKER.name],
            index_name=INDEX_NAME,
        )
        result = "created"
    except Exception as error:  # noqa: BLE001
        result = outcome(error)
    out(f"e4  index {INDEX_NAME!r} ({len(INDEX_NAME)}): {result}")
    out(f"    after the index:        {longest_internal(workspace)}")


def main() -> None:
    session = open_session()
    directory = tempfile.mkdtemp(prefix="names_")
    out = Printer(directory)
    try:
        workspace = gdb.file_gdb(session, directory=directory, name="probe")
        out("== a. layer name length ==")
        length_cases(session, out, workspace)
        out("== b. characters ==")
        character_cases(session, out, workspace)
        out("== c. case ==")
        case_cases(session, out, workspace)
        out("== d. workspace directory name ==")
        workspace_cases(session, out, directory)
        out("== e. internal file names ==")
        internal_file_cases(session, out, directory)
    finally:
        shutil.rmtree(directory, ignore_errors=True)


if __name__ == "__main__":
    main()
