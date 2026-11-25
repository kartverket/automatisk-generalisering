# Slice 1c evidence: the scratch manager

**Status:** PREPARATION, 2026-11-25, limits not yet established. Opened for the change
that lifts `staging/workspace.py` and `staging/scratch.py` and implements
`ScratchFileManager.create_workspaces` through `TableOps.create_workspace` (A5.7, A29,
T2.12, T2.13). Before the manager is drafted, two by-hand checks establish the name and
path limits it will enforce, so the limits are measured rather than assumed. Pod output
must open on both Linux and Windows: the system runs only in the Linux image (ADR-0018
Direction 6), and Windows matters because a person opens scratch dumps and transfer
directories there. The image cannot answer the Windows half, so there are two scripts;
the result sections below are filled from pasted output only.

## What each check asks

`docs/refactor/temp/slice_1c_name_limits_probe.py`, run as a module in the image with the
command in its docstring. Synthetic names and empty datasets under a temporary directory;
the directory's path is printed as `<base>`.

- **a. Layer name length.** A feature class and a table at 159, 160, 161 and 200
  characters in one fresh file geodatabase. Answers whether the 160-character limit the
  manager would enforce is the engine's, whether an over-long name is refused or
  truncated, and whether the two kinds differ.
- **b. Characters.** A table under `2nd`, `_x`, `x1`, `a-b`, `aæ`, `aø`, `aå` and
  `a__b`, each with what `ValidateTableName` returns for the name. Answers which of the
  reject-only name check's rules the engine itself enforces, whether it rewrites instead
  of refusing, and whether the scope's `__` trail separator and a non-ASCII handle name
  survive.
- **c. Case.** `Roads` with a marker field, then `roads`, with the overwrite setting as
  the session applies it. Answers whether two names differing only in case are refused,
  coexist, or the second overwrites the first; the manager's collision check compares
  exact strings, and this says whether that is enough.
- **d. Workspace name.** File geodatabases whose directory name is 250, 255 and 256
  bytes. Answers what the engine does at the filesystem's 255-byte name limit, which
  bounds the workspace stem the manager renders from the call identity.
- **e. Internal file names.** The longest file name inside a fresh `.gdb` directory,
  digits masked, when empty, after a feature class, after a table, and after an attribute
  index with a 40-character name. Answers how long the engine's internal names get and
  whether an index name reaches a file name; on a system with a path limit, a `.gdb` may
  sit no deeper than the limit less that length, and the Windows check reads the length
  at run time rather than assuming it.

`docs/refactor/temp/slice_1c_windows_paths_check.py`, run by the architect by hand on
Windows with a short base folder on the command line. It imports nothing from `ag`. It is
an observation of what Windows and Pro do with files the system writes, not a test
environment for the system (ADR-0018 AR-R10 is not reopened).

- **1a.** The `LongPathsEnabled` registry value, read only.
- **1b.** A folder at total path 247, 248 and 249 characters and a file at 258, 259 and
  260, padded with nested synthetic folders. Answers where the `MAX_PATH` margins bind
  for a long-path-aware process; read together with 1a, since Python on Windows declares
  itself long-path aware and these rows may all succeed with the registry value set
  whatever Explorer or Pro do. The second manual step, opening and copying the deepest
  1b folder in Explorer, is what says whether a person can.
- **1c.** A zip archive whose deepest member crosses 260 characters when extracted,
  extracted with the standard library; extraction in Explorer is the first manual step
  the script asks for. Answers whether a scratch dump with deep paths opens. The zip
  stands in for the scratch dump's archive format, which is not decided (ADR-0021 ST-D26
  packs a transfer directory as one object and names no format).
- **2a.** Under Pro's Python only: feature classes whose catalog path is 255, 259, 260,
  261 and 300 characters against a geodatabase path of fixed length. Answers whether the
  catalog path is bounded on Windows and where.
- **2b.** Under Pro's Python only: the longest internal file name of 2a's geodatabase,
  read at run time, then geodatabases at depths where that name ends at total path 258,
  259, 260 and 261 while the catalog path of a feature class in each stays under 260,
  with the same outcomes per step. Separates "the layer name counts against the limit"
  from "the internal files count", and locates the margin if they do.

## Engine run: the name limits probe

*Placeholder. Filled from the output the architect pastes after running the probe in the
image; nothing here is stated until then.*

## Observation on the architect's machine: Windows paths

*Placeholder. Filled from the output the architect pastes after running the check by
hand on Windows, with the Explorer extraction noted as a manual step. An observation on
one machine, not an engine result.*

## What the limits settle for the manager

*Placeholder. Written once both sections above are filled: the layer-name budget, the
name legality rules the engine already enforces and the ones the manager must add, the
case rule, and the workspace-stem bound.*
