# Slice 1c evidence: the scratch manager

**Status:** PARTLY FILLED, 2026-11-25: both scripts have run and the rows the paste shows
are recorded below; the rows a terminal folded away, and the Explorer steps, are still
placeholders. Opened for the change that lifts `staging/workspace.py` and `staging/scratch.py` and implements
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

Run by the architect in the image on 2026-11-25 with the command in the probe's docstring.
The paste folded 101 lines, so rows a4t, b1 to b8, c1, c2, d1 to d3 and e1 to e4 are
not recorded yet; what follows is what the visible lines show.

- **a. Layer name length.** At 159 and at 160 a feature class and a table were both
  created, `Exists` answered true and the listing gained the requested name (a1f, a1t,
  a2f, a2t). At 161 both were refused with `EngineError (from ExecuteError)` carrying
  `ERROR 160331: The table name is invalid`, `Exists` answered false and the listing gained
  nothing (a3f, a3t). At 200 the feature class was refused with the same classes (a4f; the
  message and a4t are in the folded lines). So the limit is 160 for both kinds, and an
  over-long name is refused, not truncated.
- **b. Characters.** *Placeholder: in the folded lines.*
- **c. Case.** *Placeholder: in the folded lines.*
- **d. Workspace name.** *Placeholder: in the folded lines.*
- **e. Internal file names.** *Placeholder: in the folded lines.*

## Observation on the architect's machine: Windows paths

Run by the architect on 2026-11-25. Part 1 ran under Pro's Python 3.13, since no other
Python was on the path; part 2 under the same interpreter. An observation on one machine,
not an engine result. The paste folded the start of the output, so 1a and the file rows
of 1b are not recorded yet.

- **1a.** *Placeholder: in the folded lines.*
- **1b.** The deepest folder created had a total path of 247 characters, so the folder at
  248 was not created. The file rows are in the folded lines.
- **1c.** After the standard library's extraction, the members at 49, 74, 99, 124, 149,
  174, 199, 224 and 249 characters existed and the member at 274 did not. Whether the
  extraction raised or skipped is in the folded lines.
- **Manual steps.** *Placeholder: the architect has not yet reported the Explorer
  extraction or the copy of the deepest 1b folder.*
- **2a.** The geodatabase at a total path of 140 was created. Feature classes whose
  catalog paths totalled 255, 259, 260, 261 and 300 characters, with names of 114 to 159
  characters, were every one created, present to `Exists`, listed, and opened by a search
  cursor that read zero rows. The catalog path is not bounded at 260 under Pro.
- **2b.** The longest internal file name of the shallow geodatabase was 48 characters.
  Geodatabases placed so that their longest internal file path ended at 258, 259, 260 and
  261 were created, and a two-character feature class in each was created, present, listed
  and opened; the longest internal file path was read back at each of the four totals. So
  Pro's own file layer writes past 260 on this machine, while the same process's Python
  stopped at a folder of 248 and lost a zip member at 274: the tools that copy and extract
  are what bind, not the engine.

## What the limits settle for the manager

Written from the rows recorded above; the rows still in the folded lines are noted where
they would bear on a rule. A34 states the rules; `staging/workspace.py` declares the
numbers.

- **Layer-name budget.** 160, the engine's own limit for both kinds (a2, a3), with no
  path term: catalog paths of 300 opened under Pro (2a), so a layer name counts toward no
  path limit.
- **Workspace name.** Bounded so that a geodatabase's longest internal file, 48
  characters (2b), fits a file path of 259 under a root allowance of 100: a workspace
  name of at most 110 characters, suffix included. That bound is below the folder limit
  less the allowance (247 less 100) and below the Linux name limit of 255 bytes, so one
  check covers all three; the loose-files directory is the workspace name without its
  suffix and is covered by the same check, leaving a loose file 52 characters. The file
  limit of 259 rests on A34 and the 1b file rows, which are still folded; the folder
  limit of 247 is in the visible 1b line.
- **Legality.** The manager refuses anything but ASCII letters, digits and underscores
  starting with a letter or underscore, and never rewrites. Which of those rules the engine
  itself enforces, and whether it rewrites, is row b, still folded; the manager's rule is
  the stricter one either way, since a name legal on both systems must be ASCII.
- **Case.** Row c is still folded; A34's rule, that names are unique without regard to
  case, is the one the manager applies.
- **Workspace-stem bound on Linux.** Row d is still folded; the 110-character bound above
  is well under 255 bytes for an ASCII name, so the row cannot move the rule.
