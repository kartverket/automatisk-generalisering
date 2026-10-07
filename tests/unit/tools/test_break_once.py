"""The break-it-once engine's pure logic, fed with captured pytest output.

What: the summary-line matcher, the verdict, the baseline parser, needle application and
the line-ending round trip, each on strings and bytes the real runs produced. No
subprocess, so these run inside the normal suite and fail whenever the engine is edited.
The scenarios that need pytest running are `python -m tools.break_once --self-check`.
"""

from __future__ import annotations

from pathlib import Path

from tools.break_once import engine

T_OPS = "tests/unit/core/test_operation_classification.py"
T_ERR = "tests/unit/core/test_errors.py"
NODE = f"{T_OPS}::test_the_bare_injected_base_is_rejected"
PARAM = f"{T_ERR}::test_every_error_survives_a_pickle_round_trip"


def _case(*targets: str) -> engine.Case:
    return engine.Case(
        "X", "probe", "src/ag/core/operations.py", (("a", "b"),), targets
    )


NOT_FOUND = (
    f"ERROR: not found: /home/user/repo/{T_OPS}::test_this_name_does_not_exist\n"
    "(no match in any of [<Module test_operation_classification.py>])\n\n"
    "no tests ran in 0.01s\n"
)
ONE_FAILED = (
    "F                                                                        [100%]\n"
    f"FAILED {NODE} - Failed: DID NOT RAISE <class 'TypeError'>\n"
    "1 failed in 0.02s\n"
)
PARAM_FAILED = (
    "..F                                                                      [100%]\n"
    f"PASSED {PARAM}[ag.core.errors.AgError]\n"
    f"PASSED {PARAM}[ag.core.errors.InjectionError]\n"
    f"FAILED {PARAM}[ag.core.errors._Probe] - TypeError: _Probe.__init__() missing 1\n"
    "1 failed, 2 passed in 0.02s\n"
)
MODULE_ERROR = (
    f"ERROR {T_OPS} - TypeError: worked: parameter 'roads' is annotated\n"
    "1 error in 0.05s\n"
)
MEMBER_ERROR = (
    f"ERROR {T_OPS}::test_x - fixture 'missing' not found\n1 error in 0.05s\n"
)
CLEAN = f"PASSED {NODE}\n1 passed in 0.01s\n"
CLEAN_PARAM = (
    f"PASSED {PARAM}[ag.core.errors.AgError]\n"
    f"PASSED {PARAM}[ag.core.errors.InjectionError]\n"
    "2 passed in 0.01s\n"
)
CLEAN_MODULE = f"PASSED {T_OPS}::test_a\nPASSED {T_OPS}::test_b\n2 passed in 0.01s\n"
SKIPPED = f"PASSED {NODE}\nSKIPPED [1] {T_OPS}:12: needs ArcPy\n1 passed, 1 skipped in 0.01s\n"


# ---------------------------------------------------------------------------
# The matcher
# ---------------------------------------------------------------------------


def test_a_failed_line_reports_its_node_id() -> None:
    assert engine.reported("FAILED|ERROR", NODE, ONE_FAILED)


def test_a_parametrised_node_id_is_reported_through_its_parameter() -> None:
    assert engine.reported("FAILED", PARAM, PARAM_FAILED)
    assert engine.reported("PASSED", PARAM, PARAM_FAILED)


def test_not_found_is_never_a_report_of_the_target() -> None:
    stale = f"{T_OPS}::test_this_name_does_not_exist"
    assert not engine.reported("FAILED|ERROR", stale, NOT_FOUND)


def test_a_module_target_is_reported_by_its_own_error_line_only() -> None:
    assert engine.reported("ERROR", T_OPS, MODULE_ERROR)
    assert not engine.reported("ERROR", T_OPS, MEMBER_ERROR)
    assert engine.reported("ERROR", T_OPS, MEMBER_ERROR, members=True)


def test_a_prefix_of_another_node_id_does_not_match() -> None:
    assert not engine.reported("FAILED", f"{T_OPS}::test_the_bare", ONE_FAILED)


# ---------------------------------------------------------------------------
# The verdict
# ---------------------------------------------------------------------------


def test_verdict_accepts_exit_1_with_every_target_reported() -> None:
    assert engine.verdict(_case(NODE), 1, ONE_FAILED)
    assert engine.verdict(_case(PARAM), 1, PARAM_FAILED)
    assert engine.verdict(_case(T_OPS), 1, MODULE_ERROR)


def test_verdict_rejects_a_stale_target_under_exit_4() -> None:
    assert not engine.verdict(
        _case(f"{T_OPS}::test_this_name_does_not_exist"), 4, NOT_FOUND
    )


def test_verdict_rejects_any_exit_code_but_1() -> None:
    assert not engine.verdict(_case(NODE), 0, CLEAN)
    assert not engine.verdict(_case(NODE), 2, ONE_FAILED)
    assert not engine.verdict(_case(NODE), 4, ONE_FAILED)


def test_verdict_rejects_a_missing_target() -> None:
    assert not engine.verdict(_case(NODE, f"{T_OPS}::test_other"), 1, ONE_FAILED)


def test_verdict_rejects_a_module_target_whose_member_failed_instead() -> None:
    assert not engine.verdict(_case(T_OPS), 1, MEMBER_ERROR)


# ---------------------------------------------------------------------------
# The baseline
# ---------------------------------------------------------------------------


def test_baseline_passes_on_a_clean_run() -> None:
    assert engine.baseline_problem(_case(NODE), 0, CLEAN) is None
    assert engine.baseline_problem(_case(PARAM), 0, CLEAN_PARAM) is None
    assert engine.baseline_problem(_case(T_OPS), 0, CLEAN_MODULE) is None


def test_baseline_rejects_a_skipped_line() -> None:
    problem = engine.baseline_problem(_case(NODE), 0, SKIPPED)
    assert problem is not None and "SKIPPED" in problem


def test_baseline_rejects_a_missing_passed_line_and_a_nonzero_exit() -> None:
    assert engine.baseline_problem(_case(NODE), 4, NOT_FOUND) is not None
    assert engine.baseline_problem(_case(NODE), 1, ONE_FAILED) is not None
    assert (
        engine.baseline_problem(_case(NODE, f"{T_OPS}::test_other"), 0, CLEAN)
        is not None
    )


# ---------------------------------------------------------------------------
# Needles and line endings
# ---------------------------------------------------------------------------


def test_mutate_requires_exactly_one_match_and_appends_on_an_empty_needle() -> None:
    assert engine.mutate("a\nb\n", (("a", "x"),)) == "x\nb\n"
    assert engine.mutate("a\na\n", (("a", "x"),)) is None
    assert engine.mutate("b\n", (("a", "x"),)) is None
    assert engine.mutate("b\n", (("", "tail\n"),)) == "b\ntail\n"


def test_a_crlf_file_matches_lf_needles_and_restores_byte_exact(tmp_path: Path) -> None:
    path = tmp_path / "sample.py"
    original = (
        b"def guard(x: int) -> int:\r\n    if x < 0:\r\n        raise ValueError(x)\r\n"
    )
    path.write_bytes(original)
    data, text = engine.read_source(path)
    assert "\r" not in text
    mutated = engine.mutate(text, (("    if x < 0:", "    if False:"),))
    assert mutated is not None
    engine.write_source(path, mutated, like=data)
    written = path.read_bytes()
    assert b"if False:" in written
    assert b"\n" not in written.replace(b"\r\n", b"")
    path.write_bytes(data)
    assert path.read_bytes() == original


def test_an_lf_file_stays_lf(tmp_path: Path) -> None:
    path = tmp_path / "sample.py"
    path.write_bytes(b"a\nb\n")
    data, text = engine.read_source(path)
    engine.write_source(path, text.replace("a", "x"), like=data)
    assert path.read_bytes() == b"x\nb\n"


# ---------------------------------------------------------------------------
# The tables
# ---------------------------------------------------------------------------


COLLECTED = (
    f"{NODE}\n"
    f"{T_OPS}::test_a_positional_parameter_is_rejected\n"
    f"{PARAM}[ag.core.errors.AgError]\n"
    f"{PARAM}[ag.core.errors.InjectionError]\n"
    "\n62 tests collected in 0.03s\n"
)


def test_uncollected_names_every_target_the_collection_did_not_list() -> None:
    """The preflight cannot trust the exit code: a module given as a target makes pytest
    exit 0 for a missing node id inside it, so the collected ids are compared instead."""
    present = (NODE, PARAM, T_OPS)
    assert engine.uncollected(present, COLLECTED) == []
    stale = f"{T_OPS}::test_this_name_does_not_exist"
    assert engine.uncollected((*present, stale), COLLECTED) == [stale]
    absent_module = "tests/unit/core/test_handles.py"
    assert engine.uncollected((T_ERR,), COLLECTED) == []
    assert engine.uncollected((absent_module,), COLLECTED) == [absent_module]
    assert engine.uncollected((f"{T_OPS}::test_a_positional",), COLLECTED) == [
        f"{T_OPS}::test_a_positional"
    ]


def test_every_case_set_has_unique_ids_and_targets() -> None:
    for case_set in engine.load_sets():
        ids = [case.id for case in case_set.cases]
        assert len(ids) == len(set(ids)), case_set.name
        assert all(case.tests for case in case_set.cases), case_set.name
        assert case_set.suite
