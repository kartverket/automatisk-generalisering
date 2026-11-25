"""By-hand check of what Windows, and ArcGIS Pro's Python where present, do with long
paths in files the system writes: an observation on the architect's machine, not a test
environment for the system. The system runs only in the Linux image (ADR-0018
Direction 6) and the Pro interpreter is not an environment of it (ADR-0018 AR-R10, not
reopened here); Windows matters because a person opens scratch dumps and transfer
directories there, and the scratch manager's limits must leave what a pod wrote
openable.

Run by hand, from any Python 3.10 or later, with a base folder of your choosing; the
folder should be short, since every length below is a total path length and a long base
leaves no room:

    python slice_1c_windows_paths_check.py C:\\t

Under ArcGIS Pro's Python the second part runs as well, since `arcpy` imports there:

    "C:\\Program Files\\ArcGIS\\Pro\\bin\\Python\\envs\\arcgispro-py3\\python.exe" ^
        slice_1c_windows_paths_check.py C:\\t

This module imports nothing from `ag`; the project is not installed where it runs.

Part 1, plain Python:
  - reads and prints the `LongPathsEnabled` value under
    `HKLM\\SYSTEM\\CurrentControlSet\\Control\\FileSystem` (read-only; absent is printed
    as absent);
  - pads under the base folder with nested synthetic folders and creates a folder whose
    total path is 247, 248 and 249 characters, and a file whose total path is 258, 259
    and 260, printing for each the outcome (`created`, or the exception class and the
    first line of its message) and whether the path is seen afterwards. Read together
    with the registry value: Python on Windows declares itself long-path aware, so with
    `LongPathsEnabled` set these rows may all succeed whatever Explorer or Pro do with
    the same paths, which is why the manual step below also opens the deepest folder;
  - writes a zip archive holding a small tree whose deepest member, once extracted under
    the base, has a total path over 260 characters, extracts it with the standard
    library and prints what happened to each member. Extracting the same archive in
    Explorer, and opening and copying the deepest folder of the previous part there, are
    the architect's manual steps; the instruction for them is printed last. The zip
    stands in for the scratch dump's archive format, which is not decided.

Part 2, only when `arcpy` imports:
  - creates a file geodatabase under a padded folder and feature classes whose catalog
    path (geodatabase path, separator, layer name) is 255, 259, 260, 261 and 300
    characters, by varying the layer name against a geodatabase path of fixed length,
    printing for each whether creation, `Exists`, listing and opening a search cursor
    succeed;
  - reads the longest internal file name of that geodatabase at run time, then creates
    geodatabases at depths where that name ends at total path 258, 259, 260 and 261
    characters while the catalog path of a feature class `fc` in each stays under 260,
    and prints the same outcomes for it. That separates "the layer name counts against
    the limit" from "the internal files count", and locates the margin if they do.

Every printed line has the base folder replaced by `<base>`, so no user name or machine
path appears in the paste. Nothing is deleted: the deep tree is what Explorer is asked
to open. Removing it afterwards may need the long-path form of the base,
`rmdir /s /q \\\\?\\<base>` in a command prompt. Synthetic names and empty datasets
only.
"""

from __future__ import annotations

import io
import os
import sys
import zipfile
from collections.abc import Callable

FOLDER_TOTALS = (247, 248, 249)
FILE_TOTALS = (258, 259, 260)
CATALOG_TOTALS = (255, 259, 260, 261, 300)
GDB_PATH_LENGTH = 140
"""Fixed geodatabase path length for the catalog-path rows, so the layer name alone
varies: the names are then 114, 118, 119, 120 and 159 characters, all within the
160-character layer limit, so a refusal is about the path and not the name. The base
folder must be shorter than 134 characters for the padding to reach this exactly."""
INTERNAL_END_TOTALS = (258, 259, 260, 261)
"""Total path lengths at which the longest internal file of a geodatabase is made to
end; the geodatabase's own path is that less the name's length less one."""
PAD_SEGMENT = 24
"""Length of each padding folder's name; the last one is cut to hit the total
exactly."""
REGISTRY_KEY = r"SYSTEM\CurrentControlSet\Control\FileSystem"
REGISTRY_VALUE = "LongPathsEnabled"
ZIP_NAME = "deep_tree.zip"
EXTRACT_DIR = "zip_out"


class Printer:
    def __init__(self, base: str) -> None:
        self._base = base

    def __call__(self, text: str) -> None:
        print(text.replace(self._base, "<base>"))


def outcome(error: BaseException) -> str:
    first = str(error).splitlines()[0] if str(error) else ""
    return f"{type(error).__name__}: {first}"


def padded_parent(base: str, *, total: int) -> str:
    """A folder under `base` whose path is exactly `total` characters, created with
    every intermediate folder."""
    path = base
    depth = 0
    while len(path) < total:
        room = total - len(path) - 1
        if room < 1:
            raise ValueError(f"cannot pad {len(base)} characters to exactly {total}")
        name = (f"p{depth}" + "x" * PAD_SEGMENT)[: min(PAD_SEGMENT, room)]
        path = os.path.join(path, name)
        depth += 1
    os.makedirs(path, exist_ok=True)
    return path


def leaf_path(base: str, *, total: int, parent_total: int) -> str:
    """A path of exactly `total` characters whose parent has `parent_total`."""
    parent = padded_parent(base, total=parent_total)
    name = "f" + "x" * (total - len(parent) - 2)
    return os.path.join(parent, name)


def seen(path: str) -> str:
    try:
        return f"exists={os.path.exists(path)}"
    except OSError as error:
        return outcome(error)


def registry(out: Printer) -> None:
    out("== 1a. LongPathsEnabled ==")
    if sys.platform != "win32":
        out(f"not Windows ({sys.platform}); no registry to read")
        return
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, REGISTRY_KEY) as key:
            value, kind = winreg.QueryValueEx(key, REGISTRY_VALUE)
        out(f"{REGISTRY_VALUE} = {value!r} (type {kind})")
    except FileNotFoundError:
        out(f"{REGISTRY_VALUE} absent")
    except OSError as error:
        out(f"{REGISTRY_VALUE}: {outcome(error)}")
    out(f"python {sys.version.split()[0]}; windows {sys.getwindowsversion()!r}")


def folders_and_files(base: str, out: Printer) -> str | None:
    """The rows at the margins; returns the deepest folder that was created, for the
    manual step."""
    out("== 1b. folder and file at the MAX_PATH margins (read with 1a) ==")
    parent_total = min(200, len(base) + 60)
    deepest: str | None = None
    for total in FOLDER_TOTALS:
        path = leaf_path(base, total=total, parent_total=parent_total)
        try:
            os.mkdir(path)
            result = "created"
            deepest = path
        except OSError as error:
            result = outcome(error)
        out(f"folder total={len(path)} -> {result}; {seen(path)}")
    for total in FILE_TOTALS:
        path = leaf_path(base, total=total, parent_total=parent_total)
        try:
            with open(path, "x", encoding="ascii") as handle:
                handle.write("x")
            result = "created"
        except OSError as error:
            result = outcome(error)
        out(f"file   total={len(path)} -> {result}; {seen(path)}")
    return deepest


def deep_zip(base: str, out: Printer, *, deepest_folder: str | None) -> None:
    out("== 1c. a zip whose deepest member crosses 260 when extracted ==")
    target = os.path.join(base, EXTRACT_DIR)
    members: list[str] = []
    relative = ""
    while len(os.path.join(target, relative, "leaf.txt")) <= 272:
        relative = os.path.join(relative, "d" + "y" * (PAD_SEGMENT - 1))
        members.append(os.path.join(relative, "leaf.txt"))
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for member in members:
            archive.writestr(member.replace(os.sep, "/"), "x")
    archive_path = os.path.join(base, ZIP_NAME)
    with open(archive_path, "wb") as handle:
        handle.write(buffer.getvalue())
    out(f"archive written: {archive_path}, {len(members)} members")
    for member in members:
        out(f"  member total when extracted: {len(os.path.join(target, member))}")
    try:
        with zipfile.ZipFile(archive_path) as archive:
            archive.extractall(target)
        result = "extractall returned"
    except Exception as error:  # noqa: BLE001  a check reports, it does not handle
        result = outcome(error)
    out(f"standard library extraction: {result}")
    for member in members:
        extracted = os.path.join(target, member)
        out(f"  {len(extracted):3} {seen(extracted)}")
    out(
        "MANUAL STEP 1: in Explorer, right-click <base>\\"
        f"{ZIP_NAME}, choose Extract All, extract to <base>\\explorer_out, and note "
        "whether it completes, skips members or shows an error, and which members "
        "exist afterwards."
    )
    folder = "none was created" if deepest_folder is None else deepest_folder
    out(
        f"MANUAL STEP 2: in Explorer, open the deepest folder created in 1b ({folder}, "
        f"{len(folder)} characters), then copy it to <base>\\copied, and note whether "
        "each step completes or what Explorer reports."
    )


def arcpy_available() -> bool:
    try:
        import arcpy  # noqa: F401
    except ImportError as error:
        print(f"== 2. arcpy not importable ({outcome(error)}); part 2 skipped ==")
        return False
    return True


def pro_outcomes(out: Printer, *, workspace: str, name: str) -> None:
    """Creation, `Exists`, listing and a search cursor for `workspace/name`."""
    import arcpy

    path = os.path.join(workspace, name)
    steps: tuple[tuple[str, Callable[[], object]], ...] = (
        (
            "create",
            lambda: arcpy.management.CreateFeatureclass(
                workspace,
                name,
                "POINT",
                spatial_reference=arcpy.SpatialReference(25833),
            ),
        ),
        ("Exists", lambda: arcpy.Exists(path)),
        (
            "listed",
            lambda: any(
                name in found
                for _, _, found in arcpy.da.Walk(workspace, datatype="FeatureClass")
            ),
        ),
        ("cursor", lambda: _rows(path)),
    )
    out(f"catalog path total={len(path)} name len={len(name)}")
    for label, step in steps:
        try:
            value = step()
            result = "ok" if label == "create" else repr(value)
        except Exception as error:  # noqa: BLE001
            result = outcome(error)
        out(f"  {label:7} -> {result}")


def _rows(path: str) -> int:
    """Opens a search cursor on `path` and counts its rows; an empty layer gives 0."""
    import arcpy

    with arcpy.da.SearchCursor(path, ["OID@"]) as cursor:
        return sum(1 for _ in cursor)


def pro_geodatabase(base: str, out: Printer, *, total: int, stem: str) -> str | None:
    """A file geodatabase whose path is exactly `total` characters; None if the tool
    refused."""
    import arcpy

    name = f"{stem}.gdb"
    parent = padded_parent(base, total=total - len(name) - 1)
    path = os.path.join(parent, name)
    try:
        arcpy.management.CreateFileGDB(parent, stem)
    except Exception as error:  # noqa: BLE001
        out(f"geodatabase total={len(path)} -> {outcome(error)}")
        return None
    out(f"geodatabase total={len(path)} -> created; Exists={arcpy.Exists(path)!r}")
    return path


def pro_catalog_paths(base: str, out: Printer) -> str | None:
    """The catalog-path rows; returns the shallow geodatabase for the internal-file
    sweep."""
    out("== 2a. catalog path length against a geodatabase path of fixed length ==")
    workspace = pro_geodatabase(base, out, total=GDB_PATH_LENGTH, stem="g")
    if workspace is None:
        return None
    for total in CATALOG_TOTALS:
        length = total - len(workspace) - 1
        name = "c" + "x" * (length - 1)
        if length > 160:
            out(
                f"catalog path total={total}: name would be {length} characters, over "
                "the 160-character layer limit; the row shows which refusal comes first"
            )
        pro_outcomes(out, workspace=workspace, name=name)
    return workspace


def longest_internal_name(workspace: str, out: Printer) -> int:
    """The length of the longest file name inside the geodatabase directory, 0 when
    the directory cannot be read."""
    try:
        return max((len(entry.name) for entry in os.scandir(workspace)), default=0)
    except OSError as error:
        out(f"  scandir of the geodatabase: {outcome(error)}")
        return 0


def pro_internal_file_sweep(base: str, out: Printer, *, shallow: str) -> None:
    out("== 2b. internal files at the margin, every catalog path under 260 ==")
    longest = longest_internal_name(shallow, out)
    out(f"longest internal file name in the shallow geodatabase: {longest} characters")
    if longest == 0:
        return
    for total in INTERNAL_END_TOTALS:
        out(f"-- internal files end at {total} --")
        workspace = pro_geodatabase(base, out, total=total - longest - 1, stem="g")
        if workspace is None:
            continue
        pro_outcomes(out, workspace=workspace, name="fc")
        seen_longest = longest_internal_name(workspace, out)
        out(f"  longest internal file path now: {len(workspace) + 1 + seen_longest}")


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: slice_1c_windows_paths_check.py <base folder>", file=sys.stderr)
        return 2
    base = os.path.abspath(argv[1])
    os.makedirs(base, exist_ok=True)
    out = Printer(base)
    out(f"base folder length: {len(base)}")
    registry(out)
    deepest_folder = folders_and_files(base, out)
    deep_zip(base, out, deepest_folder=deepest_folder)
    if arcpy_available():
        shallow = pro_catalog_paths(base, out)
        if shallow is not None:
            pro_internal_file_sweep(base, out, shallow=shallow)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
