"""Cases for the scratch manager: `staging/workspace.py` and `staging/scratch.py`, each
guard named by the test that catches it.
"""

from __future__ import annotations

from ..engine import Case, tests_in

WORKSPACE = "src/ag/staging/workspace.py"
SCRATCH = "src/ag/staging/scratch.py"
T_WORKSPACE = "tests/unit/staging/test_workspace.py"
T_SCRATCH = "tests/unit/staging/test_scratch.py"

CASES: tuple[Case, ...] = (
    Case(
        "S1",
        "per-call collision check removed",
        SCRATCH,
        (
            (
                "            if before is not None:\n"
                "                raise WorkspaceError(",
                "            if False:\n                raise WorkspaceError(",
            ),
        ),
        tests_in(
            T_SCRATCH,
            "test_a_repeated_trail_and_leaf_in_one_call_raises",
            "test_a_leaf_differing_only_in_case_raises",
        ),
    ),
    Case(
        "S2",
        "collision key narrowed to the rendered layer name",
        SCRATCH,
        (
            (
                "            key = path.casefold()\n"
                "            before = self._issued.get(key)",
                "            key = render_trail(trail, leaf).casefold()\n"
                "            before = self._issued.get(key)",
            ),
        ),
        tests_in(
            T_SCRATCH, "test_the_same_leaf_in_two_calls_gives_two_unequal_handles"
        ),
    ),
    Case(
        "S3",
        "internal collision compared with regard to case",
        SCRATCH,
        (
            (
                "            key = path.casefold()\n"
                "            before = self._issued.get(key)",
                "            key = path\n            before = self._issued.get(key)",
            ),
        ),
        tests_in(T_SCRATCH, "test_a_leaf_differing_only_in_case_raises"),
    ),
    Case(
        "S4",
        "declared collision compared with regard to case",
        SCRATCH,
        (
            (
                "        key = path.casefold()\n"
                "        before = self._declared.setdefault(key, declared)",
                "        key = path\n"
                "        before = self._declared.setdefault(key, declared)",
            ),
        ),
        tests_in(
            T_SCRATCH, "test_two_declared_handles_differing_only_in_case_are_refused"
        ),
    ),
    Case(
        "S5",
        "layer-name limit not checked",
        WORKSPACE,
        (("    if len(rendered) > LAYER_NAME_LIMIT:", "    if False:"),),
        tests_in(T_WORKSPACE, "test_render_trail_allows_the_limit_and_refuses_one_over")
        + tests_in(
            T_SCRATCH, "test_a_leaf_over_the_layer_limit_raises_without_issuing"
        ),
    ),
    Case(
        "S6",
        "workspace-name limit not checked",
        WORKSPACE,
        (("    if len(name) > WORKSPACE_NAME_LIMIT:", "    if False:"),),
        tests_in(
            T_WORKSPACE,
            "test_workspace_name_at_the_limit_passes_and_one_over_is_refused",
        ),
    ),
    Case(
        "S7",
        "name legality not checked",
        WORKSPACE,
        (("    if _NAME.fullmatch(name) is None:", "    if False:"),),
        tests_in(
            T_WORKSPACE,
            "test_illegal_names_are_refused_not_rewritten",
            "test_join_checks_the_layer_name_and_spells_the_path",
            "test_workspace_path_checks_the_stem_for_legality",
        ),
    ),
    Case(
        "S8",
        "unknown call identity not refused",
        SCRATCH,
        (
            (
                "        if workspace is None:\n            raise StagingError(",
                "        if False:\n            raise StagingError(",
            ),
        ),
        tests_in(T_SCRATCH, "test_an_unknown_call_is_refused"),
    ),
    Case(
        "S9",
        "two identities rendering alike accepted",
        SCRATCH,
        (
            (
                "        if other != call:\n            raise WorkspaceError(",
                "        if False:\n            raise WorkspaceError(",
            ),
        ),
        tests_in(
            T_SCRATCH,
            "test_two_identities_rendering_alike_without_regard_to_case_are_refused",
            "test_a_call_rendering_like_the_stage_is_refused",
        ),
    ),
    Case(
        "S10",
        "scope namespace not stamped with the call identity",
        SCRATCH,
        (
            (
                "        return ScratchScope(namespace=call, trail=(), "
                "materialize=materialize)",
                '        return ScratchScope(namespace="", trail=(), '
                "materialize=materialize)",
            ),
        ),
        tests_in(
            T_SCRATCH,
            "test_a_scope_is_bound_to_its_call_and_renders_the_trail",
            "test_the_same_leaf_in_two_calls_gives_two_unequal_handles",
        ),
    ),
    Case(
        "S11",
        "repeated call identity accepted",
        SCRATCH,
        (
            (
                "        if call in stems:\n            raise StagingError(",
                "        if False:\n            raise StagingError(",
            ),
        ),
        tests_in(T_SCRATCH, "test_a_repeated_call_identity_is_refused"),
    ),
    Case(
        "S12",
        "partition index not paired with the role",
        SCRATCH,
        (
            (
                "        if (partition_index is None) == (role is PodRole.POD):",
                "        if False:",
            ),
        ),
        tests_in(T_SCRATCH, "test_an_index_pairs_with_the_partition_role_only"),
    ),
    Case(
        "S13",
        "stage's rendered name outside the uniqueness check",
        SCRATCH,
        (
            (
                "    seen: dict[str, str] = {render_identity(stage).casefold(): stage}",
                "    seen: dict[str, str] = {}",
            ),
        ),
        tests_in(T_SCRATCH, "test_a_call_rendering_like_the_stage_is_refused"),
    ),
)

SUITE: tuple[str, ...] = ("tests/unit/staging",)
