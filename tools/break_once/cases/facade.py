"""Cases for the generic port facade: `lineage/facade.py`, the cast count, the typing
guard on `wrap`, and row 10 of `.importlinter`.
"""

from __future__ import annotations

from ..engine import Case, tests_in

FACADE = "src/ag/lineage/facade.py"
LOCAL_RUNNER = "src/ag/runtime/local.py"
GENERALIZATION_INIT = "src/ag/generalization/__init__.py"
T_UNIT = "tests/unit/lineage/test_facade.py"
T_TYPING = "tests/static/test_facade_typing.py"
T_CASTS = "tests/static/test_cast_count.py"
T_CONTRACTS = "tests/static/test_import_contracts.py"
EQUALITY = f"{T_UNIT}::test_a_call_through_the_facade_equals_the_direct_call"

CASES: tuple[Case, ...] = (
    Case(
        "F1",
        "the row shape read from the port instance instead of the Protocol",
        FACADE,
        (
            (
                "        declaration = getattr(self._protocol, name)\n",
                "        declaration = getattr(self._port, name)\n",
            ),
        ),
        tests_in(
            T_UNIT, "test_the_rows_come_from_the_protocol_and_not_from_the_adapter"
        ),
    ),
    Case(
        "F2",
        "a second cast, under an alias, in another package",
        LOCAL_RUNNER,
        (("", "\nfrom typing import cast as c  # probe\n\nPROBE = c(object, None)\n"),),
        tests_in(T_CASTS, "test_cast_call_sites_are_pinned"),
    ),
    Case(
        "F3",
        "both defences removed: an adapter method off the Protocol reachable and called",
        FACADE,
        (
            ("        if name not in self._members:\n", "        if False:\n"),
            (
                "        declaration = getattr(self._protocol, name)\n",
                "        declaration = getattr(self._protocol, name, None)\n",
            ),
        ),
        tests_in(
            T_UNIT,
            "test_a_public_name_on_the_adapter_but_off_the_protocol_is_not_reachable",
        ),
    ),
    Case(
        "F4",
        "the before hook not called",
        FACADE,
        (("            self._before(call)\n", ""),),
        tests_in(
            T_UNIT, "test_the_hooks_see_the_call_with_the_protocols_rows_in_order"
        ),
    ),
    Case(
        "F5",
        "the after hook not called",
        FACADE,
        (("            self._after(call, result)\n", ""),),
        tests_in(
            T_UNIT, "test_the_hooks_see_the_call_with_the_protocols_rows_in_order"
        ),
    ),
    Case(
        "F6",
        "wrap's port parameter widened to object, so a non-conformer is handed out",
        FACADE,
        (("    port: P,\n", "    port: object,\n"),),
        tests_in(
            T_TYPING,
            "test_a_non_conformer_is_refused_where_the_wrapped_port_is_handed_out",
        ),
    ),
    Case(
        "F7",
        "the port's result not returned",
        FACADE,
        (("            return result\n", "            return None\n"),),
        (f"{EQUALITY}[TableOps.read_rows]",),
    ),
    Case(
        "F8",
        "the parents keyword dropped before forwarding",
        FACADE,
        (
            (
                "            result = target(**kwargs)\n",
                "            result = target(\n"
                '                **{k: v for k, v in kwargs.items() if k != "parents"}\n'
                "            )\n",
            ),
        ),
        (f"{EQUALITY}[GeometryOps.explode_multipart]",),
    ),
    Case(
        "F9",
        "a positional call forwarded instead of refused",
        FACADE,
        (("            if args:\n", "            if False:\n"),),
        tests_in(
            T_UNIT, "test_a_positional_call_fails_at_the_facade_naming_the_method"
        ),
    ),
    Case(
        "F10",
        "row 10: the domain imports the facade",
        GENERALIZATION_INIT,
        (("", "\nimport ag.lineage.facade  # probe\n"),),
        (f"{T_CONTRACTS}::test_contract_is_kept[row-10-lineage-is-runtimes-alone]",),
    ),
    Case(
        "F11",
        "the dunder guard removed, so a copy probe recurses into the facade's state",
        FACADE,
        (
            (
                '        if name.startswith("_"):\n'
                "            # A dunder probe (copy, pickle, inspection) wants a plain miss, "
                "raised before\n"
                "            # any state is read: a copy in the making has none yet.\n"
                "            raise AttributeError(name)\n",
                "",
            ),
        ),
        tests_in(
            T_UNIT,
            "test_a_name_off_the_protocol_raises_and_the_facade_has_no_public_name",
        ),
    ),
)

SUITE: tuple[str, ...] = ("tests/unit/lineage", "tests/static")
