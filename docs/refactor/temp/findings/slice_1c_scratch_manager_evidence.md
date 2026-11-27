# Slice 1c evidence: the scratch manager

**Status:** FILLED, 2026-11-26: both scripts, the two Explorer steps and the marked suite
have run, and every row is recorded below from the architect's pasted output. Opened for
the change that lifts `staging/workspace.py` and `staging/scratch.py` and implements
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

Run by the architect in the image on 2026-11-26 with the command in the probe's docstring.

- **a. Layer name length.** At 159 and at 160 a feature class and a table were both
  created, `Exists` answered true and the listing gained the requested name (a1f, a1t,
  a2f, a2t). At 161 and at 200 both kinds were refused with `EngineError (from
  ExecuteError)` carrying `ERROR 160331: The table name is invalid`, `Exists` answered
  false and the listing gained nothing (a3f, a3t, a4f, a4t). So the limit is 160 for both
  kinds, and an over-long name is refused, not truncated.
- **b. Characters.** `2nd` and `a-b` were refused with the same ERROR 160331, and
  `ValidateTableName` would have rewritten them to `T2nd` and `a_b` (b1, b4). `_x`, `x1`
  and `a__b` were created and returned unchanged by `ValidateTableName` (b2, b3, b8). `aæ`,
  `aø` and `aå` were created and returned unchanged (b5 to b7). So the engine refuses a
  leading digit and a hyphen, accepts a leading underscore, a double underscore and the
  three Norwegian letters, and `ValidateTableName` rewrites rather than refuses. A34's
  ASCII-only rule is stricter than the engine, by choice: a name must open on both
  systems and be greppable as written.
- **c. Case.** With `overwriteOutput` true as the session applies it, `Roads` with a
  marker field was created (c1), then `roads` was created without error (c2); afterwards
  `Roads` listed only `OBJECTID`, the marker was gone, and the listing held `roads` alone.
  So `roads` silently replaced `Roads`: the engine treats two names differing only in case
  as one. This is the evidence for the manager's case-insensitive comparison.
- **d. Workspace name.** Geodatabase directories of 250 and 255 bytes were created and
  answered as workspaces (d1, d2). At 256 bytes `CreateFileGDB` failed with the generic
  `ERROR 999999: Something unexpected caused the tool to fail`, and nothing existed
  afterwards (d3). The engine gives no clear message at the filesystem's name limit, which
  is why the manager checks the length itself.
- **e. Internal file names.** The longest file in an empty geodatabase was
  `a#######a.EditingTemplateRelsByDestinationID.atx`, 48 characters among 54 files; it
  stayed the longest after a feature class (61 files) and after a table with a field (64
  files) (e1 to e3). An attribute index named `ix_` and 37 x's (40 characters) was created
  and added `a#######c.ix_x{37}.atx`, 54 characters, among 65 files (e4). So an index adds
  a file of 14 characters plus the index name, and an index name over 34 characters becomes
  the longest file. Nothing creates an attribute index today; `INTERNAL_FILE_NAME_LENGTH`
  stays 48 with this note beside it, and B38 carries the adjustment for when something does.

## Observation on the architect's machine: Windows paths

Run by the architect on 2026-11-26 under Pro's Python 3.13.13 on Windows 10 build 26300,
base folder 7 characters long. Both parts ran under that interpreter, since no other Python
was on the path. An observation on one machine, not an engine result.

- **1a.** `LongPathsEnabled` was 0: long paths were not enabled, so Python's long-path
  manifest had no effect and the rows below show the `MAX_PATH` margins.
- **1b.** A folder at total path 247 was created; 248 and 249 failed with
  `FileNotFoundError: [WinError 206] The filename or extension is too long`. A file at 258
  and at 259 was created; 260 failed with `FileNotFoundError: [Errno 2]`. So a file path
  is bounded at 259 and a folder path at 247.
- **1c.** The zip held ten members whose extracted totals were 49 to 274 in steps of 25.
  The standard library's extraction raised `FileNotFoundError: [WinError 3] The system
  cannot find the path specified` on the 274 member after creating the nine shorter ones:
  49 to 249 existed afterwards, 274 did not. An over-deep member fails the extraction
  rather than being skipped.
- **Explorer, step 1.** Extract All of the same zip showed one error dialog, "The file
  name(s) would be too long for the destination folder. You can shorten the file name and
  try again, or try a location that has a shorter path", for a folder item. Afterwards the
  folders at 45 to 245 and the files at 54 to 254 existed; the tenth folder, which would
  have been 270, and its file at 279 were not created. The totals are 1c's plus 5, since
  `explorer_out` is five characters longer than `zip_out`. So Explorer stops at the same
  247 folder margin as 1b, and reports the failure with a dialog rather than skipping the
  file silently.
- **Explorer, step 2.** The deepest 1b folder, at 247, opened in Explorer and copied to
  `<base>\copied` without error; the copy made the path shorter, not longer.
- **2a.** The geodatabase at a total path of 140 was created. Feature classes whose
  catalog paths totalled 255, 259, 260, 261 and 300 characters, with names of 114 to 159
  characters, were every one created, present to `Exists`, listed, and opened by a search
  cursor that read zero rows. The catalog path is not bounded at 260 under Pro.
- **2b.** The longest internal file name of the shallow geodatabase was 48 characters.
  Geodatabases placed so that their longest internal file path ended at 258, 259, 260 and
  261 were created, and a two-character feature class in each was created, present, listed
  and opened; the longest internal file path was read back at each of the four totals. So
  Pro's own file layer writes past 260 on this machine, while the same process's Python
  stopped at a folder of 248 and a file of 260 and lost a zip member at 274, and Explorer
  stopped at the same folder margin: the limit binds the tools a person copies and extracts
  with, not the engine.

## Engine run: the marked suite

Run by the architect in the image on 2026-11-26 with the command in
`docs/contributing/testing.md`: 88 collected, 29 deselected, 59 passed in 146 seconds. The
two tests of `tests/engine/arcpy/test_scratch.py` were among them: every workspace the
manager names was created as a workspace through `ArcpyTableOps` with the loose-files
directory beside the stage workspace, and the engine's internal file names in a fresh
geodatabase holding a feature class and a table fit `INTERNAL_FILE_NAME_LENGTH`.

## What the limits settle for the manager

A34 states the rules; `staging/workspace.py` declares the numbers.

- **Layer-name budget.** 160, the engine's own limit for both kinds (a2, a3), with no
  path term: catalog paths of 300 opened under Pro (2a), so a layer name counts toward no
  path limit. A rendered name over 160 is shortened by whole labels and marked with a
  window of the full name's digest, never cut (`02-runtime.md` §4.2); a declared handle's
  name has no trail to drop and is refused over 160.
- **Workspace name.** Bounded so that a geodatabase's longest internal file, 48
  characters (e1 to e3, 2b), fits a file path of 259 (1b) under a root allowance of 100: a
  workspace name of at most 110 characters, suffix included. That bound is below the folder
  limit less the allowance (247 less 100, 1b) and below the Linux name limit of 255 bytes
  (d2, d3), so one check covers all three; the loose-files directory is the workspace name
  without its suffix and is covered by the same check, leaving a loose file 52 characters.
  Workspace names are never shortened. The bound rests on the 48 of the system tables; an
  attribute index name over 34 characters would exceed it (e4, B38).
- **Legality.** The manager refuses anything but ASCII letters, digits and underscores
  starting with a letter or underscore, and never rewrites. The engine itself refuses a
  leading digit and a hyphen and accepts the Norwegian letters (b1 to b7); the manager's
  rule is the stricter one, since a name legal on both systems and greppable as written
  must be ASCII. `ValidateTableName` is never called, because it rewrites (b1, b4).
- **Case.** Names are unique without regard to case: `roads` silently replaced `Roads`
  under the session's overwrite setting (c1, c2), so every collision check compares
  casefolded names, and a shortened name's digest is taken over the casefolded full name
  so that two case variants shorten alike.
- **Workspace-stem bound on Linux.** 255 bytes is the filesystem's and the engine fails at
  256 with a generic error (d3); the 110-character bound above is under it for an ASCII
  name, so the Linux limit never binds.
