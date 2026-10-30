# Slice 1b evidence: the ArcPy session and the constrained stub

**Status:** EVIDENCE, 2026-10-30. Produced for the first pull request of slice 1b (the
constrained ArcPy stub `stubs/arcpy_constrained/arcpy/__init__.pyi`, the session
`adapters/arcpy/session.py` and `adapters/arcpy/_base.py`, the `arcpy-session-only` rule of
`tools/scan_sources.py` over the adapter root and `tests/support/arcpy`, the unit tests of the
session, the static tests of the scan and of the stub, ADR-0018 AR-D23, ADR-0021 ST-D25 and
ST-R7, A32 and B28) by `python -m tools.break_once arcpy_session`, whose case table is
`tools/break_once/cases/arcpy_session.py` (A30). Every guard broken once, with the covering
tests failing, then restored; `git status` showed the mutated files unchanged after the run,
and the set's suite was green after the last restore. No engine ran in this PR: every test is
unmarked and runs on a fake engine or on pyright. B23, the environment for `pytest -m arcpy`,
stays open and is not needed here. The by-hand checks and the cases carried to the first run
under the engine follow the report.

Case set `arcpy_session`, run by `python -m tools.break_once arcpy_session`. Per case: its targets pass on the clean tree (baseline), one source file is edited to remove the guard, the same targets must then fail, and the file is restored. The set's suite runs after the last restore.

### S1: a reference outside a guard in the adapter root

File: `src/ag/adapters/arcpy/_base.py`. Edit: append 'import arcpy  # probe' ....

Targets: test_tree_is_clean[adapters-arcpy]. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       assert [found.render() for found in findings] == []
E       assert ["_base.py:21...sion's guard"] == []
E         Left contains one more item: "_base.py:21: [arcpy-session-only] `arcpy` is referenced outside the session's guard"
E         Use -v to get more diff
FAILED tests/static/test_source_scans.py::test_tree_is_clean[adapters-arcpy]
1 failed in 0.04s
```

### S2: the same reference in the engine-touching test root

File: `tests/support/arcpy/__init__.py`. Edit: append 'import arcpy  # probe' ....

Targets: test_tree_is_clean[tests-support-arcpy]. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       assert [found.render() for found in findings] == []
E       assert ["__init__.py...sion's guard"] == []
E         Left contains one more item: "__init__.py:14: [arcpy-session-only] `arcpy` is referenced outside the session's guard"
E         Use -v to get more diff
FAILED tests/static/test_source_scans.py::test_tree_is_clean[tests-support-arcpy]
1 failed in 0.04s
```

### S3: the vendor exception named inside a guard block

File: `src/ag/adapters/arcpy/_base.py`. Edit: append 'import arcpy  # probe' ....

Targets: test_tree_is_clean[adapters-arcpy]. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       assert [found.render() for found in findings] == []
E       AssertionError: assert ['_base.py:26... the session'] == []
E         Left contains one more item: '_base.py:26: [arcpy-session-only] an `except` on an engine class belongs to the session'
E         Use -v to get more diff
FAILED tests/static/test_source_scans.py::test_tree_is_clean[adapters-arcpy]
1 failed in 0.04s
```

### S4: the allowlist widened to the base class

File: `tools/scan_sources.py`. Edit: `frozenset({"session.py"})` -> `frozenset({"session.py", "_base.py"})`.

Targets: test_scan_tree_exempts_only_the_allowlisted_file[arcpy-session-only]. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       assert [(found.path, found.rule) for found in findings] == [(other_file, rule)]
E       AssertionError: assert [] == [('_base.py',...ession-only')]
E         Right contains one more item: ('_base.py', 'arcpy-session-only')
E         Use -v to get more diff
FAILED tests/static/test_source_scans.py::test_scan_tree_exempts_only_the_allowlisted_file[arcpy-session-only]
1 failed in 0.04s
```

### S5: any with block exempts its body

File: `tools/scan_sources.py`. Edit: `if _is_guard(item.context_expr):` -> `if True:`.

Targets: test_rule_fires_on_reference_outside_guard[with-block-that-is-not-the-guard]. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
                id="callable-passed-as-argument",
>       assert engine_findings(source) == [ARCPY]
E       AssertionError: assert [] == ['arcpy-session-only']
E         Right contains one more item: 'arcpy-session-only'
E         Use -v to get more diff
FAILED tests/static/test_source_scans.py::test_rule_fires_on_reference_outside_guard[with-block-that-is-not-the-guard]
1 failed in 0.04s
```

### S6: a submodule import form, which resolves past the stub

File: `src/ag/adapters/arcpy/_base.py`. Edit: append 'from arcpy.management import Delete  # probe' ....

Targets: test_tree_is_clean[adapters-arcpy]. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       assert [found.render() for found in findings] == []
E       AssertionError: assert ['_base.py:19...ast the stub'] == []
E         Left contains one more item: '_base.py:19: [arcpy-session-only] `from arcpy.management import ...` resolves past the stub'
E         Use -v to get more diff
FAILED tests/static/test_source_scans.py::test_tree_is_clean[adapters-arcpy]
1 failed in 0.04s
```

### S7: getattr on the engine inside a guard block

File: `src/ag/adapters/arcpy/_base.py`. Edit: append 'import arcpy  # probe' ....

Targets: test_tree_is_clean[adapters-arcpy]. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       assert [found.render() for found in findings] == []
E       AssertionError: assert ['_base.py:24...ind the stub'] == []
E         Left contains one more item: '_base.py:24: [arcpy-session-only] `getattr` reaches the engine behind the stub'
E         Use -v to get more diff
FAILED tests/static/test_source_scans.py::test_tree_is_clean[adapters-arcpy]
1 failed in 0.04s
```

### S8: deferred code inside a guard counts as guarded

File: `tools/scan_sources.py`. Edit: `if isinstance(node, _DEFERRED):` -> `if False:`.

Targets: test_rule_fires_on_reference_outside_guard[lambda-written-inside-the-guard]. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
                id="callable-passed-as-argument",
>       assert engine_findings(source) == [ARCPY]
E       AssertionError: assert [] == ['arcpy-session-only']
E         Right contains one more item: 'arcpy-session-only'
E         Use -v to get more diff
FAILED tests/static/test_source_scans.py::test_rule_fires_on_reference_outside_guard[lambda-written-inside-the-guard]
1 failed in 0.04s
```

### R1: the tool called outside the guard

File: `src/ag/adapters/arcpy/session.py`. Edit: `with self.guard(name):` -> `result = tool(**arguments)`.

Targets: test_a_vendor_failure_from_a_tool_is_an_engine_error_from_the_original. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>           session.run_tool("management.Delete", in_data="x")
>           raise self._raises
E           tests.unit.adapters.arcpy.test_session.FakeExecuteError: boom
FAILED tests/unit/adapters/arcpy/test_session.py::test_a_vendor_failure_from_a_tool_is_an_engine_error_from_the_original
1 failed in 0.06s
```

### R2: the failure messages dropped from the context

File: `src/ag/adapters/arcpy/session.py`. Edit: `context=ErrorContext(tool=what, tool_messages=lines),` -> `context=ErrorContext(tool=what),`.

Targets: test_a_tool_failure_carries_the_tool_and_the_drained_lines. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
        assert str(info.value) == "arcpy: management.Delete failed: boom"
>       assert info.value.context.tool_messages == ("boom", "ERROR 000732: x", "Failed")
E       AssertionError: assert () == ('boom', 'ERR... x', 'Failed')
E         Right contains 3 more items, first extra item: 'boom'
E         Use -v to get more diff
FAILED tests/unit/adapters/arcpy/test_session.py::test_a_tool_failure_carries_the_tool_and_the_drained_lines
1 failed in 0.06s
```

### R3: the success drain dropped

File: `src/ag/adapters/arcpy/session.py`. Edit: `lines = _lines(result.getMessages())` -> `lines = ()`.

Targets: test_a_successful_tool_logs_its_own_messages. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       assert "management.Delete: ('Start', 'Done')" in caplog.text
E       assert "management.Delete: ('Start', 'Done')" in 'DEBUG    ag.adapters.arcpy.session:session.py:118 management.Delete: ()\n'
E        +  where 'DEBUG    ag.adapters.arcpy.session:session.py:118 management.Delete: ()\n' = <_pytest.logging.LogCaptureFixture object at 0x705f80a6e7b0>.text
FAILED tests/unit/adapters/arcpy/test_session.py::test_a_successful_tool_logs_its_own_messages
1 failed in 0.06s
```

### R4: the cause dropped

File: `src/ag/adapters/arcpy/session.py`. Edit: `) from error` -> `) from None`.

Targets: test_a_vendor_failure_in_the_guard_is_an_engine_error_from_the_original. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       assert info.value.__cause__ is failure
E       AssertionError: assert None is FakeExecuteError('bad')
E        +  where None = EngineError('arcpy: cursor failed: bad').__cause__
E        +    where EngineError('arcpy: cursor failed: bad') = <ExceptionInfo EngineError('arcpy: cursor failed: bad') tblen=3>.value
FAILED tests/unit/adapters/arcpy/test_session.py::test_a_vendor_failure_in_the_guard_is_an_engine_error_from_the_original
1 failed in 0.06s
```

### R5: the stale buffer attached on a RuntimeError

File: `src/ag/adapters/arcpy/session.py`. Edit: `if isinstance(error, self._execute_error):` -> `if True:`.

Targets: test_a_runtime_error_inside_the_guard_carries_no_stale_buffer. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       assert info.value.context.tool_messages == ("locked",)
E       AssertionError: assert ('locked', 'stale') == ('locked',)
E         Left contains one more item: 'stale'
E         Use -v to get more diff
FAILED tests/unit/adapters/arcpy/test_session.py::test_a_runtime_error_inside_the_guard_carries_no_stale_buffer
1 failed in 0.06s
```

### E1: the environment not applied

File: `src/ag/adapters/arcpy/session.py`. Edit: `_apply(engine, ENVIRONMENT)` -> `pass`.

Targets: test_construction_applies_the_environment_once. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       assert env.overwriteOutput is True
E       AttributeError: 'types.SimpleNamespace' object has no attribute 'overwriteOutput'
FAILED tests/unit/adapters/arcpy/test_session.py::test_construction_applies_the_environment_once
1 failed in 0.06s
```

### G1: the pass-through removed: every exception wrapped

File: `src/ag/adapters/arcpy/session.py`. Edit: delete `if not _is_engine_error(error, self._execute_error):`.

Targets: test_an_ag_error_inside_the_guard_passes_through, test_an_adapter_defect_inside_the_guard_passes_through. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       assert info.value is error
E       AssertionError: assert EngineError('arcpy: cursor failed: unknown field') is PortContractError('unknown field')
E        +  where EngineError('arcpy: cursor failed: unknown field') = <ExceptionInfo EngineError('arcpy: cursor failed: unknown field') tblen=3>.value
>               raise KeyError("shape")
E               KeyError: 'shape'
>           with session.guard("cursor"):
>           raise EngineError(
                f"arcpy: {what} failed: {error}",
E           ag.ports.errors.EngineError: arcpy: cursor failed: 'shape'
FAILED tests/unit/adapters/arcpy/test_session.py::test_an_ag_error_inside_the_guard_passes_through
FAILED tests/unit/adapters/arcpy/test_session.py::test_an_adapter_defect_inside_the_guard_passes_through
2 failed in 0.08s
```

### G2: the exact class widened to every RuntimeError subclass

File: `src/ag/adapters/arcpy/session.py`. Edit: `type(error) is RuntimeError` -> `isinstance(error, RuntimeError)`.

Targets: test_a_runtime_error_subclass_inside_the_guard_passes_through. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>               raise NotImplementedError("later")
E               NotImplementedError: later
>           with session.guard("cursor"):
>           raise EngineError(
                f"arcpy: {what} failed: {error}",
E           ag.ports.errors.EngineError: arcpy: cursor failed: later
FAILED tests/unit/adapters/arcpy/test_session.py::test_a_runtime_error_subclass_inside_the_guard_passes_through
1 failed in 0.08s
```

### X1: the stub widened with a toolbox

File: `stubs/arcpy_constrained/arcpy/__init__.pyi`. Edit: append 'class management:' ....

Targets: test_the_stub_refuses_tools_env_and_the_exception_name. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       assert refused == [
E       assert [2, 5, 8] == [2, 4, 5, 8]
E         At index 1 diff: 5 != 4
E         Right contains one more item: 8
E         Use -v to get more diff
FAILED tests/static/test_arcpy_stub.py::test_the_stub_refuses_tools_env_and_the_exception_name
1 failed in 1.17s
```

### After the last restore

```
140 passed in 5.44s
```

## By hand

### The pyright hook refuses a tool call in the adapter root

A probe module `src/ag/adapters/arcpy/probe_tmp.py` holding `import arcpy` and
`arcpy.management.Delete("x")`, with the project configuration as committed
(`[[tool.pyright.executionEnvironments]]` for `src/ag/adapters/arcpy` with the stub first on
`extraPaths`), fails the pyright hook, and the scan refuses the same line. The probe was
removed afterwards; `git status` clean.

```
$ uv run --locked --extra dev pyright
  src/ag/adapters/arcpy/probe_tmp.py:3:1 - error: Type of "management" is unknown (reportUnknownMemberType)
  src/ag/adapters/arcpy/probe_tmp.py:3:1 - error: Type of "Delete" is unknown (reportUnknownMemberType)
  src/ag/adapters/arcpy/probe_tmp.py:3:7 - error: "management" is not a known attribute of module "arcpy" (reportAttributeAccessIssue)
3 errors, 0 warnings, 0 informations
$ uv run --locked --extra dev python tools/scan_sources.py
src/ag/adapters/arcpy/probe_tmp.py:3: [arcpy-session-only] `arcpy` is referenced outside the session's guard
1 problem(s) found
```

### The stub under a configuration of its own

Pyright 1.1.399, strict, on a scratch probe with the real stub on `extraPaths` and no ArcPy
on the interpreter. This is what `tests/static/test_arcpy_stub.py` pins, split into what the
stub owns (asserted everywhere) and what the missing interpreter package produces (asserted
only without ArcPy).

| probe line | result |
|---|---|
| `import arcpy.management` | reportMissingImports |
| `from arcpy.management import Delete` | reportMissingImports |
| `from arcpy import env` | reportAttributeAccessIssue |
| `from arcpy import management` | reportAttributeAccessIssue |
| `arcpy.management.Delete("x")` after `import arcpy` only | reportAttributeAccessIssue |
| `arcpy.management.Delete("x")` after `import arcpy.management` | reportUnknownMemberType only |
| `arcpy.env.workspace = ...` | reportAttributeAccessIssue |
| `except arcpy.ExecuteError` | reportAttributeAccessIssue |
| `Delete("y")`, `management.Delete("z")` through the imports | nothing |
| `getattr(arcpy, "management")` | nothing |
| `arcpy.__dict__["management"]` | nothing |

The last two rows are why the scan exists; the submodule rows are why it refuses every
import form but `import arcpy`.

### The execution environments list `src` again

With the stub as the only extra path of the adapter root's execution environment, the first
`ag` import under that root resolved through the editable install and strict mode reported
`reportMissingTypeStubs` for `ag.core.errors`, `ag.ports.errors` and
`ag.adapters.arcpy.session`. An execution environment's `extraPaths` replace the top-level
ones, so `pyproject.toml` now lists `src` after the stub for both roots, and `tools` as well
for `tests/support/arcpy`. The stub stays first and so outranks site-packages.

### Row 8 with the factory in the session module

`open_session()` in `session.py` carries the one `import arcpy` under the adapter. A lazy
import in `runtime/` was tried on a scratch copy and broke row 8; with the factory:

```
$ uv run --locked --extra dev lint-imports
Row 8: a vendor library is imported only by its adapter KEPT (1 ignored import)
Contracts: 24 kept, 0 broken.
```

## Carried to the first run under the engine

The session's drain rule and catch set are assumptions until a marked run confirms them.
These are the cases, to be run under an ArcGIS Pro Python environment once B23 is settled:

- **W1** A misspelt keyword to `run_tool` after a successful tool: `TypeError` unwrapped, no
  `EngineError`, and the message buffer not read.
- **W2** A real tool failure after a successful tool: the failing tool's own lines in the
  context, not the earlier tool's.
- **W3** Any tool failure after engine work that surfaces as a `RuntimeError` (candidates: a
  wrapper raising after the engine started; an output locked by an open cursor). If none is
  found, the drain rule is recorded as unrefuted, not confirmed; if one is, it argues for
  draining the buffer on that class too.
- **W4** The environment values read back from the engine after construction, with the
  values the session applied: EPSG 25833, XY tolerance 0.1 m, XY resolution 0.01 m,
  overwrite on.
- **W5** The probe module in the adapter root under the Pro interpreter: the `pyproject.toml`
  wiring with ArcPy present, including the submodule-import forms the scan catches and
  pyright, with ArcPy resolvable, is expected not to.
- **W6** The exception class a cursor raises on a missing field, a locked dataset and a bad
  where clause; confirms or corrects the guard's catch set, and records whether ArcPy raises a
  `RuntimeError` subclass anywhere.

## Deferred by name

- `TableOps.read_rows` docstring precondition line: the row IO pull request.
- The adapter-owned capability record, first member `explode_multipart`: the next pull
  request.
- The per-row guard cost: the timing pull request.
- B29 (where pydantic would sit): not written; a separate change on the architect's
  confirmation.
