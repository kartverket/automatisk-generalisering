"""Cases for the ArcPy session: the guard, the drain, the environment, the scan rule
that keeps engine access in the session module, and the constrained stub.
"""

from __future__ import annotations

from ..engine import Case, tests_in

SESSION = "src/ag/adapters/arcpy/session.py"
BASE = "src/ag/adapters/arcpy/_base.py"
SUPPORT = "tests/support/arcpy/__init__.py"
SCANNER = "tools/scan_sources.py"
STUB = "stubs/arcpy_constrained/arcpy/__init__.pyi"
T_SESSION = "tests/unit/adapters/arcpy/test_session.py"
T_SCANS = "tests/static/test_source_scans.py"
T_STUB = "tests/static/test_arcpy_stub.py"

ADAPTER_TREE_CLEAN = tests_in(T_SCANS, "test_tree_is_clean[adapters-arcpy]")
REFERENCE_PROBE = '\nimport arcpy  # probe\n\nPROBE = arcpy.Exists("x")\n'
CONTEXT_LINE = "                context=ErrorContext(tool=what, tool_messages=lines),\n"

CASES: tuple[Case, ...] = (
    Case(
        "S1",
        "a reference outside a guard in the adapter root",
        BASE,
        (("", REFERENCE_PROBE),),
        ADAPTER_TREE_CLEAN,
    ),
    Case(
        "S2",
        "the same reference in the engine-touching test root",
        SUPPORT,
        (("", REFERENCE_PROBE),),
        tests_in(T_SCANS, "test_tree_is_clean[tests-support-arcpy]"),
    ),
    Case(
        "S3",
        "the vendor exception named inside a guard block",
        BASE,
        (
            (
                "",
                "\nimport arcpy  # probe\n\n\n"
                "def probe(session: ArcpySession) -> None:\n"
                '    with session.guard("probe"):\n'
                "        try:\n"
                "            pass\n"
                "        except arcpy.ExecuteError:\n"
                "            pass\n",
            ),
        ),
        ADAPTER_TREE_CLEAN,
    ),
    Case(
        "S4",
        "the allowlist widened to the base class",
        SCANNER,
        (
            (
                'frozenset({"session.py"})',
                'frozenset({"session.py", "_base.py"})',
            ),
        ),
        tests_in(
            T_SCANS,
            "test_scan_tree_exempts_only_the_allowlisted_file[arcpy-session-only]",
        ),
    ),
    Case(
        "S5",
        "any with block exempts its body",
        SCANNER,
        (
            (
                "            if _is_guard(item.context_expr):\n",
                "            if True:\n",
            ),
        ),
        tests_in(
            T_SCANS,
            "test_rule_fires_on_reference_outside_guard[with-block-that-is-not-the-guard]",
        ),
    ),
    Case(
        "S6",
        "a submodule import form, which resolves past the stub",
        BASE,
        (("", "\nfrom arcpy.management import Delete  # probe\n"),),
        ADAPTER_TREE_CLEAN,
    ),
    Case(
        "S7",
        "getattr on the engine inside a guard block",
        BASE,
        (
            (
                "",
                "\nimport arcpy  # probe\n\n\n"
                "def probe(session: ArcpySession) -> object:\n"
                '    with session.guard("probe"):\n'
                '        return getattr(arcpy, "management")\n',
            ),
        ),
        ADAPTER_TREE_CLEAN,
    ),
    Case(
        "S8",
        "deferred code inside a guard counts as guarded",
        SCANNER,
        (
            (
                "    if isinstance(node, _DEFERRED):\n",
                "    if False:\n",
            ),
        ),
        tests_in(
            T_SCANS,
            "test_rule_fires_on_reference_outside_guard[lambda-written-inside-the-guard]",
        ),
    ),
    Case(
        "R1",
        "the tool called outside the guard",
        SESSION,
        (
            (
                "        with self.guard(name):\n"
                "            result = tool(**arguments)\n"
                "            lines = _lines(result.getMessages())\n",
                "        result = tool(**arguments)\n"
                "        with self.guard(name):\n"
                "            lines = _lines(result.getMessages())\n",
            ),
        ),
        tests_in(
            T_SESSION,
            "test_a_vendor_failure_from_a_tool_is_an_engine_error_from_the_original",
        ),
    ),
    Case(
        "R2",
        "the failure messages dropped from the context",
        SESSION,
        ((CONTEXT_LINE, "                context=ErrorContext(tool=what),\n"),),
        tests_in(
            T_SESSION, "test_a_tool_failure_carries_the_tool_and_the_drained_lines"
        ),
    ),
    Case(
        "R3",
        "the success drain dropped",
        SESSION,
        (
            (
                "            lines = _lines(result.getMessages())\n",
                "            lines = ()\n",
            ),
        ),
        tests_in(T_SESSION, "test_a_successful_tool_logs_its_own_messages"),
    ),
    Case(
        "R4",
        "the cause dropped",
        SESSION,
        (
            (
                CONTEXT_LINE + "            ) from error\n",
                CONTEXT_LINE + "            ) from None\n",
            ),
        ),
        tests_in(
            T_SESSION,
            "test_a_vendor_failure_in_the_guard_is_an_engine_error_from_the_original",
        ),
    ),
    Case(
        "R5",
        "the stale buffer attached on a RuntimeError",
        SESSION,
        (
            (
                "            if isinstance(error, self._execute_error):\n",
                "            if True:\n",
            ),
        ),
        tests_in(
            T_SESSION, "test_a_runtime_error_inside_the_guard_carries_no_stale_buffer"
        ),
    ),
    Case(
        "E1",
        "the environment not applied",
        SESSION,
        (("            _apply(engine, ENVIRONMENT)\n", "            pass\n"),),
        tests_in(T_SESSION, "test_construction_applies_the_environment_once"),
    ),
    Case(
        "G1",
        "the pass-through removed: every exception wrapped",
        SESSION,
        (
            (
                "            if not _is_engine_error(error, self._execute_error):\n"
                "                raise\n",
                "",
            ),
        ),
        tests_in(
            T_SESSION,
            "test_an_ag_error_inside_the_guard_passes_through",
            "test_an_adapter_defect_inside_the_guard_passes_through",
        ),
    ),
    Case(
        "G2",
        "the exact class widened to every RuntimeError subclass",
        SESSION,
        (("type(error) is RuntimeError", "isinstance(error, RuntimeError)"),),
        tests_in(
            T_SESSION, "test_a_runtime_error_subclass_inside_the_guard_passes_through"
        ),
    ),
    Case(
        "X1",
        "the stub widened with a toolbox",
        STUB,
        (
            (
                "",
                "\nclass management:\n"
                "    @staticmethod\n"
                "    def Delete(in_data: str, /) -> None: ...\n",
            ),
        ),
        tests_in(T_STUB, "test_the_stub_refuses_tools_env_and_the_exception_name"),
    ),
)

SUITE: tuple[str, ...] = ("tests/unit/adapters/arcpy", "tests/static")
