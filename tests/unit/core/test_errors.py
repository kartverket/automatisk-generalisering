"""The error root, its context, and the one way a layer adds to it.

What: `fill_context` fills empty fields only and caps the row sample; every `AgError`
subclass in the package survives a pickle round-trip with its type, message and context,
because a partitioned run's failure record is a serialised error.

How: the subclasses are discovered, not listed: every `errors.py` under the package is
imported and the class tree below `AgError` walked, so a new error module is covered the
day it lands. The boundary: an `AgError` subclass lives in a module named `errors.py`;
one defined elsewhere is covered only if something imported it first. Error modules
import the standard library and `ag.core` only. That rule is checked from each module's
source, and a module that breaks it is left out of the import step, so this file still
collects where no engine is installed, the violation is reported by its own test, and
every error that passes unpickles on a machine without an engine.
"""

from __future__ import annotations

import ast
import importlib
import pickle
import sys
from collections.abc import Iterator, Sequence
from pathlib import Path

import pytest

import ag
from ag.core.errors import ROW_INDEX_CAP, AgError, ErrorContext, fill_context

PACKAGE = Path(ag.__file__).resolve().parent


def _error_modules() -> list[tuple[str, Path]]:
    return [
        (".".join(("ag", *path.relative_to(PACKAGE).with_suffix("").parts)), path)
        for path in sorted(PACKAGE.rglob("errors.py"))
    ]


def _imported_modules(module: str, path: Path) -> set[str]:
    """Every module the file imports, as a full dotted name.

    A relative import is resolved against the module's own package, so `from .x import`
    in `ag.ports.errors` names `ag.ports.x`.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    package = module.rsplit(".", 1)[0]
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0:
                names.add(node.module or "")
            else:
                base = (
                    package.rsplit(".", node.level - 1)[0]
                    if node.level > 1
                    else package
                )
                names.add(f"{base}.{node.module}" if node.module else base)
    return names


def _forbidden_imports(module: str, path: Path) -> set[str]:
    """Imports that are neither standard library nor under `ag.core`."""
    return {
        name
        for name in _imported_modules(module, path)
        if not (name == "ag.core" or name.startswith("ag.core."))
        and name.split(".")[0] not in sys.stdlib_module_names
    }


def _error_types() -> list[type[AgError]]:
    for module, path in _error_modules():
        if not _forbidden_imports(module, path):
            importlib.import_module(module)
    found: set[type[AgError]] = set()
    pending: list[type[AgError]] = [AgError]
    while pending:
        cls = pending.pop()
        if cls.__module__.startswith("ag."):
            found.add(cls)
        pending.extend(cls.__subclasses__())
    return sorted(found, key=_qualified)


def _qualified(cls: type) -> str:
    return f"{cls.__module__}.{cls.__qualname__}"


# ---------------------------------------------------------------------------
# What an error module may import
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("module", "path"), _error_modules(), ids=[m for m, _ in _error_modules()]
)
def test_error_modules_import_only_the_standard_library_and_core(
    module: str, path: Path
) -> None:
    """Why: an error module that imported an engine would stop this file collecting
    where the engine is absent, and would make its errors unpicklable there."""
    assert _forbidden_imports(module, path) == set(), module


def test_the_import_rule_sees_relative_and_dotted_imports(tmp_path: Path) -> None:
    """The rule reads the source, so it is checked here on sources of its own. The
    module name given resolves relative imports; the file can live anywhere."""
    cases: dict[str, set[str]] = {
        "from ag.core.errors import AgError\nimport json\n": set(),
        "import ag.adapters.arcpy\n": {"ag.adapters.arcpy"},
        "from ag.ports import toolbox\n": {"ag.ports"},
        "from . import toolbox\n": {"ag.ports"},
        "from .errors import PortError\n": {"ag.ports.errors"},
        "import arcpy\nfrom shapely import geometry\n": {"arcpy", "shapely"},
    }
    probe = tmp_path / "errors.py"
    for source, expected in cases.items():
        probe.write_text(source, encoding="utf-8")
        assert _forbidden_imports("ag.ports.errors", probe) == expected, source


# ---------------------------------------------------------------------------
# The context and the root
# ---------------------------------------------------------------------------


def test_an_error_without_context_carries_an_empty_one() -> None:
    error = AgError("boom")
    assert str(error) == "boom"
    assert error.context == ErrorContext()


def test_fill_context_fills_empty_fields_only() -> None:
    error = AgError(
        "boom", context=ErrorContext(method="dissolve", tool="PairwiseDissolve")
    )
    fill_context(error, method="select", port="geometry", handle="Network.roads")
    assert error.context.method == "dissolve"
    assert error.context.tool == "PairwiseDissolve"
    assert error.context.port == "geometry"
    assert error.context.handle == "Network.roads"


def test_fill_context_keeps_an_existing_row_sample() -> None:
    error = AgError("boom", context=ErrorContext(row_indices=(1, 2), row_count=2))
    fill_context(error, row_indices=range(100))
    assert error.context.row_indices == (1, 2)
    assert error.context.row_count == 2


def test_fill_context_caps_the_row_sample_and_derives_the_count() -> None:
    error = AgError("boom")
    fill_context(error, row_indices=range(100))
    assert error.context.row_indices == tuple(range(ROW_INDEX_CAP))
    assert error.context.row_count == 100


def test_fill_context_takes_an_explicit_count_over_the_derived_one() -> None:
    error = AgError("boom")
    fill_context(error, row_indices=(8701, 11698), row_count=4000)
    assert error.context.row_indices == (8701, 11698)
    assert error.context.row_count == 4000


def test_fill_context_keeps_indices_and_count_as_one_pair() -> None:
    """An inner layer that knew only the count is not paired with an outer layer's
    rows, and the other way round."""
    only_count = AgError("boom", context=ErrorContext(row_count=7))
    fill_context(only_count, row_indices=(1, 2, 3))
    assert only_count.context.row_indices == ()
    assert only_count.context.row_count == 7

    only_rows = AgError("boom", context=ErrorContext(row_indices=(5,)))
    fill_context(only_rows, row_count=9000)
    assert only_rows.context.row_indices == (5,)
    assert only_rows.context.row_count == 1


def test_fill_context_reads_a_generator_only_up_to_the_cap_when_the_count_is_given() -> (
    None
):
    produced = iter(range(10_000))
    error = AgError("boom")
    fill_context(error, row_indices=produced, row_count=10_000)
    assert error.context.row_indices == tuple(range(ROW_INDEX_CAP))
    assert next(produced) == ROW_INDEX_CAP


class _ArrayLike[T]:
    """Stands in for an engine array: iterable, and ambiguous as a truth value."""

    def __init__(self, values: Sequence[T]) -> None:
        self._values = values

    def __bool__(self) -> bool:
        raise ValueError("the truth value of an array is ambiguous")

    def __iter__(self) -> Iterator[T]:
        return iter(self._values)


class _EngineInt(int):
    """Stands in for an engine integer such as a 64-bit NumPy scalar."""


def test_fill_context_accepts_array_like_rows_and_messages() -> None:
    error = AgError("boom")
    fill_context(
        error,
        row_indices=_ArrayLike([_EngineInt(3), _EngineInt(4)]),
        tool_messages=_ArrayLike(["ERROR 000210"]),
    )
    assert error.context.row_indices == (3, 4)
    assert all(type(index) is int for index in error.context.row_indices)
    assert error.context.row_count == 2
    assert error.context.tool_messages == ("ERROR 000210",)


def test_a_directly_constructed_context_normalises_its_sequences() -> None:
    context = ErrorContext(
        row_indices=[_EngineInt(7), 8],  # pyright: ignore[reportArgumentType]
        tool_messages=["a", "b"],  # pyright: ignore[reportArgumentType]
    )
    assert context.row_indices == (7, 8)
    assert all(type(index) is int for index in context.row_indices)
    assert context.tool_messages == ("a", "b")
    assert hash(context) == hash(
        ErrorContext(row_indices=(7, 8), tool_messages=("a", "b"))
    )


def test_a_float_row_position_is_refused_rather_than_truncated() -> None:
    with pytest.raises(TypeError):
        ErrorContext(row_indices=(1.5,))  # pyright: ignore[reportArgumentType]


def test_a_bare_string_is_one_tool_message() -> None:
    context = ErrorContext(tool_messages="ERROR 000210")  # pyright: ignore[reportArgumentType]
    assert context.tool_messages == ("ERROR 000210",)
    error = AgError("boom")
    fill_context(error, tool_messages="ERROR 000210")
    assert error.context.tool_messages == ("ERROR 000210",)


def test_a_directly_constructed_context_is_capped_and_counted() -> None:
    context = ErrorContext(row_indices=tuple(range(100)))
    assert context.row_indices == tuple(range(ROW_INDEX_CAP))
    assert context.row_count == 100
    explicit = ErrorContext(row_indices=(1, 2), row_count=50)
    assert explicit.row_count == 50


def test_fill_context_never_replaces_the_operation() -> None:
    error = AgError("boom")
    fill_context(error, operation="resolve_ramps")
    fill_context(error, operation="thin_road_network", tool_messages=("ERROR 000210",))
    assert error.context.operation == "resolve_ramps"
    assert error.context.tool_messages == ("ERROR 000210",)


# ---------------------------------------------------------------------------
# Every error in the package survives a process boundary
# ---------------------------------------------------------------------------


def test_discovery_finds_the_root_and_the_injection_error() -> None:
    names = [cls.__name__ for cls in _error_types()]
    assert "AgError" in names
    assert "InjectionError" in names


@pytest.mark.parametrize("error_type", _error_types(), ids=_qualified)
def test_every_error_survives_a_pickle_round_trip(error_type: type[AgError]) -> None:
    context = ErrorContext(
        operation="resolve_ramps", method="dissolve", row_indices=(1,)
    )
    original = error_type("the message", context=context)
    restored = pickle.loads(pickle.dumps(original))
    assert type(restored) is error_type
    assert str(restored) == "the message"
    assert restored.context == context
