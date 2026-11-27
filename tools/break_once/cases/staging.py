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
                "                if _casefolded(before.identity) == identity:\n"
                "                    raise WorkspaceError(",
                "                if False:\n                    raise WorkspaceError(",
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
                "                key = path.casefold()\n"
                "                before = self._issued.get(key)",
                "                key = layer.casefold()\n"
                "                before = self._issued.get(key)",
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
                "                key = path.casefold()\n"
                "                before = self._issued.get(key)",
                "                key = path\n"
                "                before = self._issued.get(key)",
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
        "layer-name limit not checked at the join",
        WORKSPACE,
        (("    if len(legal_name(layer)) > LAYER_NAME_LIMIT:", "    if False:"),),
        tests_in(T_WORKSPACE, "test_join_refuses_a_layer_name_over_the_limit")
        + tests_in(T_SCRATCH, "test_a_declared_handle_over_the_layer_limit_is_refused"),
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
    Case(
        "S14",
        "over-long layer name not shortened",
        WORKSPACE,
        (
            (
                "    if len(full) <= LAYER_NAME_LIMIT:\n        return full",
                "    if True:\n        return full",
            ),
        ),
        tests_in(
            T_WORKSPACE,
            "test_a_name_at_the_limit_is_unchanged_and_one_over_is_shortened",
        )
        + tests_in(
            T_SCRATCH, "test_a_long_trail_is_shortened_and_the_manifest_reads_it_back"
        ),
    ),
    Case(
        "S15",
        "digest taken over the name with regard to case",
        WORKSPACE,
        (
            (
                "    return hashlib.sha256(full.casefold().encode()).hexdigest()",
                "    return hashlib.sha256(full.encode()).hexdigest()",
            ),
        ),
        tests_in(T_WORKSPACE, "test_names_differing_only_in_case_shorten_alike"),
    ),
    Case(
        "S16",
        "digest taken over the leaf instead of the full name",
        WORKSPACE,
        (
            (
                "    digits = digest(full)[start : start + DIGEST_LENGTH]",
                "    digits = digest(leaf)[start : start + DIGEST_LENGTH]",
            ),
        ),
        tests_in(T_WORKSPACE, "test_the_digest_is_of_the_full_name"),
    ),
    Case(
        "S17",
        "leaf dropped from a shortened name",
        WORKSPACE,
        (
            (
                "    return LAYER_SEPARATOR.join((*((first,) if fits else ()), mark, "
                "*kept, leaf))",
                "    return LAYER_SEPARATOR.join((*((first,) if fits else ()), mark, "
                "*kept))",
            ),
        ),
        tests_in(
            T_WORKSPACE,
            "test_a_shortened_name_keeps_the_leaf_the_tail_and_the_first_label",
        ),
    ),
    Case(
        "S18",
        "taken shortened name not probed",
        SCRATCH,
        (
            (
                "            for window in range(DIGEST_WINDOWS):",
                "            for window in range(1):",
            ),
        ),
        tests_in(T_SCRATCH, "test_a_taken_shortened_name_probes_the_next_window"),
    ),
    Case(
        "S19",
        "probe window not recorded in the manifest",
        SCRATCH,
        (
            (
                "                        path=path, call=call, trail=trail, leaf=leaf, "
                "window=window",
                "                        path=path, call=call, trail=trail, leaf=leaf, "
                "window=0",
            ),
        ),
        tests_in(T_SCRATCH, "test_a_taken_shortened_name_probes_the_next_window"),
    ),
    Case(
        "S20",
        "probe loop not bounded by the digest's windows",
        SCRATCH,
        (
            (
                "            for window in range(DIGEST_WINDOWS):",
                "            for window in range(10**9):",
            ),
        ),
        tests_in(T_SCRATCH, "test_every_window_taken_raises"),
    ),
)

SUITE: tuple[str, ...] = ("tests/unit/staging",)
