"""`docs/user_guide/scratch.md` and `scratch_samples.py` agree, and the page is true.

What: every `<!-- sample: key -->` fence on the page equals the block of the same key in
`scratch_samples.py`; every `<!-- names: key -->` fence lists the layer names the sample
issues, in order; every `<!-- manifest: key -->` fence is the manifest entries read back;
every `<!-- error: key -->` fence is the whole message the sample raises; every
`<!-- pattern: key -->` fence is the pattern of that name in `ag.core.handles`; the one
`<!-- handle: key -->` fence is a handle's name beside its layer name. The page names
this test and the two modules it documents name the page, so each side points at the
other.

How: the fences are read with one regular expression per marker kind, the samples run
over the memory fakes with a fixed root, so paths and messages are the same on every
machine. A key on one side without its partner fails as a set difference, naming the key.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import pytest

from ag.adapters.fakes.memory.store import MemoryStore
from ag.core import handles
from tests.support.cases import multilines
from tests.unit.docs import scratch_samples as samples

ROOT = Path(__file__).resolve().parents[3]
PAGE = ROOT / "docs" / "user_guide" / "scratch.md"
DOCUMENTED = (
    ROOT / "src" / "ag" / "core" / "handles.py",
    ROOT / "src" / "ag" / "staging" / "scratch.py",
)
"""The modules whose docstrings name the page."""

SAMPLE_BLOCK = re.compile(r"^# sample: (\w+)\n(.*?)^# end: \1\n", re.M | re.S)
PAGE_FENCE = re.compile(
    r"^<!-- (sample|names|manifest|error|pattern|handle): (\w+) -->\n"
    r"```(?:python|text)\n(.*?)^```\n",
    re.M | re.S,
)
MANIFEST_CASES = ("case_shortened", "case_probe")
"""The naming cases whose manifest entries the page shows."""
PATTERNS = {
    "LABEL_PATTERN": handles.LABEL_PATTERN,
    "TAG_PATTERN": handles.TAG_PATTERN,
}
"""The patterns the page quotes, by the name each is declared under."""


def module_blocks() -> dict[str, str]:
    source = Path(samples.__file__).read_text(encoding="utf-8")
    return {key: body.strip() for key, body in SAMPLE_BLOCK.findall(source)}


def page_fences(kind: str) -> dict[str, str]:
    text = PAGE.read_text(encoding="utf-8")
    found = {
        key: body.strip()
        for found_kind, key, body in PAGE_FENCE.findall(text)
        if found_kind == kind
    }
    return found


def names_of(pod: samples.ScratchFileManager) -> list[str]:
    return [os.path.basename(path) for path in pod.manifest()]


def test_every_sample_block_is_on_the_page_and_equal() -> None:
    blocks = module_blocks()
    fences = page_fences("sample")
    assert set(blocks) == set(fences)
    for key, body in blocks.items():
        assert fences[key] == body, key


def test_the_page_shows_names_for_every_sample_and_nothing_else() -> None:
    shown = set(page_fences("names"))
    assert shown == {"layout", *samples.OPERATIONS, *samples.CASES}
    assert set(page_fences("manifest")) == set(MANIFEST_CASES)
    assert set(page_fences("error")) == set(samples.ERRORS)
    assert set(page_fences("pattern")) == set(PATTERNS)
    assert set(page_fences("handle")) == {"handle_name"}


def test_the_layout_is_as_shown() -> None:
    pod = samples.partition_pod(MemoryStore())
    shown = page_fences("names")["layout"].splitlines()
    assert shown == [
        pod.stage_workspace(),
        pod.loose_files(),
        pod.operation_workspace(samples.CALL),
    ]


@pytest.mark.parametrize("key", sorted(samples.OPERATIONS))
def test_an_operation_sample_issues_the_names_shown(key: str) -> None:
    store = MemoryStore()
    tb = samples.memory_toolbox(store)
    pod = samples.partition_pod(store)
    source = pod.handle(samples.Roads.source)
    case = multilines()
    store.write(source, schema=case.schema, rows=case.rows)
    output = pod.handle(samples.Roads.thinned)
    samples.OPERATIONS[key](
        source=source, output=output, tb=tb, scratch=pod.scope_for(samples.CALL)
    )
    assert names_of(pod) == page_fences("names")[key].splitlines()
    assert all(store.present(path) for path in pod.manifest())
    assert tb.table.exists(input=output)


@pytest.mark.parametrize("key", sorted(samples.CASES))
def test_a_naming_case_renders_the_names_shown(key: str) -> None:
    pod = samples.CASES[key]()
    assert names_of(pod) == page_fences("names")[key].splitlines()


@pytest.mark.parametrize("key", MANIFEST_CASES)
def test_a_manifest_reads_back_as_shown(key: str) -> None:
    pod = samples.CASES[key]()
    shown = page_fences("manifest")[key].splitlines()
    assert shown == [repr(entry) for entry in pod.manifest().values()]


@pytest.mark.parametrize("key", sorted(samples.ERRORS))
def test_an_error_sample_raises_the_message_shown(key: str) -> None:
    kind, trigger = samples.ERRORS[key]
    with pytest.raises(kind) as caught:
        trigger()
    assert str(caught.value) == page_fences("error")[key]


@pytest.mark.parametrize("key", sorted(PATTERNS))
def test_a_pattern_is_quoted_as_declared(key: str) -> None:
    assert page_fences("pattern")[key] == PATTERNS[key].pattern


def test_a_handle_is_named_with_the_trail_separator_and_its_layer_with_two_underscores() -> (
    None
):
    created = samples.handle_name()
    shown = page_fences("handle")["handle_name"].splitlines()
    assert shown == [
        f"name: {created.name}",
        f"layer: {os.path.basename(os.fspath(created))}",
    ]


def test_the_testing_sample_passes() -> None:
    samples.test_parts_explodes_into_its_own_scratch()


def test_the_page_and_the_modules_name_each_other() -> None:
    assert Path(__file__).relative_to(ROOT).as_posix() in PAGE.read_text(
        encoding="utf-8"
    )
    page = PAGE.relative_to(ROOT).as_posix()
    for module in DOCUMENTED:
        assert page in module.read_text(encoding="utf-8"), module.name
