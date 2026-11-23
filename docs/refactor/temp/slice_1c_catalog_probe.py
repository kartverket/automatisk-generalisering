"""By-hand probe for the catalog methods: what the engine's `Exists` and `Describe` answer
at the margins `TableOps.exists`, `data_type_of` and `create_workspace` rely on, and what
`Exists` costs against the agreed band.

Run inside the ArcPy image from the repository root, as a module, with `src` and the root
on the path and no dev tools, since the engine writes into `__main__` on import:

    docker run --rm -v "$PWD":/work:ro -w /work \\
      -e PYTHONPATH=/work/src:/work -e PYTHONDONTWRITEBYTECODE=1 \\
      ghcr.io/kartverket/arcpy-linux:12.1 \\
      python -m docs.refactor.temp.slice_1c_catalog_probe

What it does, on synthetic data under a temporary directory:

1. Creates a file geodatabase through the port and prints what `Describe` reports for it:
   `dataType`, against the adapter's `WORKSPACE_DATA_TYPE`, and `workspaceFactoryProgID`.
2. Asks `Exists` and `Describe` about: a missing dataset in that geodatabase; a missing
   `.gdb`; a `.gdb` under a missing parent folder; under a folder whose permissions were
   removed inside the temporary directory, an absent `.gdb`, a geodatabase with one table
   created there before the folder was locked, and that table; the memory workspace itself
   and a missing dataset in it. Per path: the `Exists` answer or the exception class, and
   the `Describe` `dataType` or the exception class and message. The adapter's `exists`
   returns the engine's answer; whether the engine keeps "absent" apart from
   "unreachable" is what the locked rows show, read with the process's effective uid
   printed first, since as root the removed permissions block ordinary access to nothing.
3. Runs the file geodatabase tool against a `.gdb` under a missing parent and under the
   unreadable folder, and prints the exception class and message: the adapter relies on
   the engine's own failure there, wrapped as `EngineError` naming the tool. Then the
   tool, through the port, on the geodatabase that exists behind the locked folder: the
   port's refusal of a taken path rests on `Exists`, which answers False there, so the
   outcome shows what the tool does to a geodatabase it cannot read; after the
   permissions are restored, whether the table in it is still there.
4. Times `Exists`: 20 repeated calls on one seeded table in the file geodatabase and
   5 first calls on fresh tables, then the same in the memory workspace, printed as
   min, median and max in seconds, the way Describe was timed before. The band: 0.1 to
   0.5 s per call is acceptable, 1 to 5 s is not.
5. Last, and on a throwaway geodatabase of its own: seeds a table, runs the file
   geodatabase tool on that geodatabase's path with the session's overwrite setting as
   applied, and prints whether the table is still there afterwards. The port refuses an
   existing path before the tool for this reason; the run shows the reason holds.

Observations only: nothing here asserts, no value of any row is printed, and the output
is pasted into the evidence file. The folder whose permissions are removed is restored
before the directory is deleted. Nothing after `open_session` names the `datetime`
class, which the engine rebinds in `__main__`.
"""

from __future__ import annotations

import os
import shutil
import stat
import statistics
import tempfile
import time
from collections.abc import Callable

from ag.adapters.arcpy.session import ArcpySession, open_session
from ag.adapters.arcpy.support.dataset_schema import WORKSPACE_DATA_TYPE
from ag.adapters.arcpy.support.dataset_writer import create_table
from ag.adapters.arcpy.table_ops import ArcpyTableOps
from ag.adapters.arcpy.table_ops.catalog import FILE_GDB_TOOL
from ag.ports import Field, FieldType
from ag.ports.workspace_format import WorkspaceFormat
from tests.support.arcpy import gdb
from tests.support.fake_arcpy import MEMORY_WORKSPACE
from tests.support.gdb_cases import handle_at

REPEATED = 20
FRESH = 5


def describe_workspace(session: ArcpySession, path: str) -> None:
    with session.guard("Describe"):
        import arcpy

        described = arcpy.Describe(path)
        print(
            f"Describe({path!r}).dataType = {described.dataType!r}; equals "
            f"WORKSPACE_DATA_TYPE: {described.dataType == WORKSPACE_DATA_TYPE}"
        )
        print(f"workspaceFactoryProgID = {described.workspaceFactoryProgID!r}")


def exists_and_describe(session: ArcpySession, label: str, path: str) -> None:
    """The two engine answers for one path, each as its value or its exception."""
    with session.guard("Exists"):
        import arcpy

        try:
            answer: object = arcpy.Exists(path)
        except Exception as error:  # noqa: BLE001  a probe reports, it does not handle
            answer = f"{type(error).__name__}: {error}"
    with session.guard("Describe"):
        import arcpy

        try:
            kind: object = arcpy.Describe(path).dataType
        except Exception as error:  # noqa: BLE001
            kind = f"{type(error).__name__}: {error}"
    print(f"{label:34} Exists -> {answer!r}; Describe -> {kind!r}")


def create_attempt(session: ArcpySession, label: str, path: str) -> None:
    """The file geodatabase tool on `path`, its outcome as a line."""
    try:
        ArcpyTableOps(session=session).create_workspace(
            path=path, fmt=WorkspaceFormat.FILE_GDB
        )
    except Exception as error:  # noqa: BLE001
        context = getattr(error, "context", None)
        tool = getattr(context, "tool", None)
        messages = getattr(context, "tool_messages", ())
        print(f"{label:34} {type(error).__name__} (tool={tool!r}): {error}")
        for line in messages:
            print(f"{'':34}   {line}")
        return
    print(f"{label:34} created")


def seconds(calls: int, body: Callable[[int], None]) -> str:
    """`body` run `calls` times, each timed; min, median and max in seconds."""
    timings: list[float] = []
    for index in range(calls):
        start = time.perf_counter()
        body(index)
        timings.append(time.perf_counter() - start)
    return (
        f"n={calls} min={min(timings):.4f} median={statistics.median(timings):.4f} "
        f"max={max(timings):.4f}"
    )


def time_exists(session: ArcpySession, workspace: str, label: str) -> None:
    field = (Field("stamp", FieldType.LONG),)
    paths = [f"{workspace}/fresh_{index}" for index in range(FRESH)]
    for path in paths:
        create_table(session, path=path, fields=field)
    ops = ArcpyTableOps(session=session)

    def repeated(_: int) -> None:
        ops.exists(input=handle_at(workspace, "fresh_0"))

    def fresh(index: int) -> None:
        ops.exists(input=handle_at(workspace, f"fresh_{index}"))

    print(f"Exists, {label}, fresh:    {seconds(FRESH, fresh)}")
    print(f"Exists, {label}, repeated: {seconds(REPEATED, repeated)}")


def overwrite_probe(session: ArcpySession, directory: str) -> None:
    """The tool on a geodatabase that holds a table, overwrite on as the session applied
    it; whether the table survives is the reason the port refuses before the tool."""
    workspace = gdb.file_gdb(session, directory=directory, name="throwaway")
    create_table(session, path=f"{workspace}/kept", fields=(Field("n", FieldType.LONG),))
    folder, name = workspace.rsplit("/", 1)
    stem = name.removesuffix(WorkspaceFormat.FILE_GDB.suffix)
    print(f"overwriteOutput as applied: {session.read_environment().overwrite_output}")
    try:
        session.run_tool(FILE_GDB_TOOL, out_folder_path=folder, out_name=stem)
        print("tool on an existing geodatabase: ran")
    except Exception as error:  # noqa: BLE001
        print(f"tool on an existing geodatabase: {type(error).__name__}: {error}")
    exists_and_describe(session, "table after the tool", f"{workspace}/kept")


def main() -> None:
    session = open_session()
    euid = os.geteuid()
    reading = (
        "root: the removed permissions block ordinary access to nothing, so the locked "
        "rows are not a reachability test"
        if euid == 0
        else "not root: the locked rows test reachability"
    )
    print(f"process euid: {euid} ({reading})")
    directory = tempfile.mkdtemp(prefix="catalog_")
    locked = f"{directory}/locked"
    os.mkdir(locked)
    try:
        print("== 1. a fresh file geodatabase ==")
        workspace = gdb.file_gdb(session, directory=directory, name="probe")
        describe_workspace(session, workspace)
        held = gdb.file_gdb(session, directory=locked, name="held")
        create_table(session, path=f"{held}/kept", fields=(Field("n", FieldType.LONG),))

        print("== 2. Exists and Describe at the margins ==")
        os.chmod(locked, 0)
        suffix = WorkspaceFormat.FILE_GDB.suffix
        for label, path in (
            ("missing dataset", f"{workspace}/nothing"),
            ("missing .gdb", f"{directory}/missing{suffix}"),
            ("missing parent folder", f"{directory}/no_folder/x{suffix}"),
            ("unreadable folder itself", locked),
            (".gdb under unreadable folder", f"{locked}/x{suffix}"),
            ("existing .gdb under it", held),
            ("table in that .gdb", f"{held}/kept"),
            ("memory workspace", MEMORY_WORKSPACE),
            ("missing dataset in memory", f"{MEMORY_WORKSPACE}/nothing"),
        ):
            exists_and_describe(session, label, path)

        print("== 3. the tool where the port expects the engine to fail ==")
        create_attempt(session, "missing parent folder", f"{directory}/no_folder/x{suffix}")
        create_attempt(session, ".gdb under unreadable folder", f"{locked}/x{suffix}")
        create_attempt(session, "existing .gdb under it, locked", held)
        os.chmod(locked, stat.S_IRWXU)
        exists_and_describe(session, "table in held.gdb, unlocked", f"{held}/kept")

        print("== 4. Exists timings ==")
        time_exists(session, workspace, "file geodatabase")
        time_exists(session, MEMORY_WORKSPACE, "memory")

        print("== 5. the tool on an existing geodatabase, overwrite as applied ==")
        overwrite_probe(session, directory)
    finally:
        os.chmod(locked, stat.S_IRWXU)
        shutil.rmtree(directory, ignore_errors=True)


if __name__ == "__main__":
    main()
