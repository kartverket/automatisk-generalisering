"""Engine-free parents resolution for a keyed dissolve. STAGING — see the findings file.

What:
    Given the dissolve key of every input row and of every output row, plus a
    `PartLocator` supplied by the adapter, produce the `(output_index, input_index)`
    parent pairs of a dissolve, in native indices. The lineage layer above maps the
    indices to `lineage_id` (A11.11); this module never sees one.

How:
    Rows are grouped by key on both sides. A key that produced exactly one output row
    is resolved by attribute alone: every input with that key is a parent of that row.
    A key that produced two or more output parts is handed to the locator as one
    `LocateRequest` naming the inputs and the candidate parts, and the locator answers
    with pairs. The locator is called once with every multi-part key so an engine can
    do a single bulk spatial join. Every returned pair is checked against the request
    that owns its input: a pair whose output is not one of that key's parts is a
    contract violation and raises, because it is exactly the cross-key hit a shared
    boundary or an overlap would produce.

    An input with no pair — a zero-length line the tool discarded, a key that produced
    no output at all — is reported in `unmatched_input_indices`, never invented. The
    adapter decides whether an unmatched input is a legitimate drop (degenerate
    geometry) or a failed precondition; this module has no geometry and cannot tell.

Why:
    This is the shared, engine-free half of option C in the findings file. The
    representation is a pair table, which every engine can produce and which the
    lineage layer already consumes; the engine-specific half is only the locator.

Precondition, stated once here and in the locator: a representative point of each
input part lies within the engine's XY tolerance of the output part it became. That
holds for a dissolve, which never moves geometry. It does not hold for collapses that
move geometry while merging; those need a native table or a bespoke matcher.

Keys are compared by equality, so the caller normalises both sides the same way:
the same field order and the same Python types (a LONG read as int on one side and as
float on the other is two keys). A null key is a legitimate group and is carried as
`None` inside the tuple.
"""

from __future__ import annotations

from collections.abc import Collection, Iterable, Sequence
from dataclasses import dataclass
from typing import Protocol, TypeAlias

DissolveKey: TypeAlias = tuple[object, ...]
"""One row's dissolve-field values, in declared field order. A one-field key is a 1-tuple."""


@dataclass(frozen=True, order=True)
class ParentPair:
    """One output row and one input row that contributed to it, both as native indices."""

    output_index: int
    input_index: int


@dataclass(frozen=True)
class LocateRequest:
    """One multi-part key: the inputs that carry it and the output parts it produced.

    The locator may only pair an input in `input_indices` with an output in
    `output_indices` of the same request. That is what makes key filtering structural
    rather than something each locator remembers to do.
    """

    input_indices: tuple[int, ...]
    output_indices: tuple[int, ...]


class PartLocator(Protocol):
    """The engine-specific half: which of a key's output parts does each input touch?"""

    def locate(self, *, requests: Sequence[LocateRequest]) -> Iterable[ParentPair]: ...


class KeyMismatchError(ValueError):
    """An output key has no input with that key, or an index appears twice.

    Either means the two key lists were not read from the dissolve that relates them,
    or were normalised differently, so nothing downstream can be trusted.
    """


class LocatorContractError(ValueError):
    """The locator returned a pair outside the request that owns its input."""


@dataclass(frozen=True)
class ParentsResolution:
    """Sorted pairs, plus every input index that ended up in no pair."""

    pairs: tuple[ParentPair, ...]
    unmatched_input_indices: tuple[int, ...]


class UnmatchedInputError(ValueError):
    """An input the dissolve could not have discarded ended up in no pair."""


def require_matched(
    *, resolution: ParentsResolution, degenerate_input_indices: Collection[int]
) -> None:
    """The adapter contract on unmatched inputs: degenerate or an error, never DROPPED.

    What: raises `UnmatchedInputError` naming every unmatched input that is not in
    `degenerate_input_indices`.
    How: a set difference; the adapter supplies the classification, since only it can
    read geometry. Degenerate means: empty geometry, or length (lines) or area
    (polygons) at or below the engine's XY tolerance. A point is never degenerate.
    Why: a dissolve never discards non-degenerate geometry, so an unmatched input that
    is not degenerate means the precondition failed or the tool misbehaved (an empty
    geometry in the input emptied a whole PairwiseDissolve output, silently, on Pro
    3.7.2). Letting the lineage layer derive DROPPED from it would be the silent-wrong
    outcome A14 and A16 rank as the worst.
    """
    degenerate = set(degenerate_input_indices)
    offending = [
        index for index in resolution.unmatched_input_indices if index not in degenerate
    ]
    if offending:
        raise UnmatchedInputError(
            f"{len(offending)} non-degenerate input(s) matched no output part; first: "
            f"{offending[:10]}. A dissolve cannot discard these; the precondition "
            "failed or the tool emitted nothing for them."
        )


def dissolve_parents(
    *,
    input_keys: Iterable[tuple[int, DissolveKey]],
    output_keys: Iterable[tuple[int, DissolveKey]],
    locator: PartLocator,
) -> ParentsResolution:
    """Resolve the parent pairs of one keyed dissolve.

    What: attribute join for single-part keys, locator lookup for multi-part keys,
    every pair validated against its key, unmatched inputs reported.
    How: see the module docstring.
    Why: the pair table is the engine-neutral representation the lineage layer needs.
    """
    inputs_by_key = _group_by_key(rows=input_keys, side="input")
    outputs_by_key = _group_by_key(rows=output_keys, side="output")

    missing = [key for key in outputs_by_key if key not in inputs_by_key]
    if missing:
        raise KeyMismatchError(
            f"{len(missing)} output key(s) have no input with that key; "
            f"first: {missing[0]!r}. The two key lists were not read from the same "
            "dissolve, or were normalised differently."
        )

    pairs: set[ParentPair] = set()
    requests: list[LocateRequest] = []
    for key, input_indices in inputs_by_key.items():
        output_indices = outputs_by_key.get(key)
        if output_indices is None:
            continue
        if len(output_indices) == 1:
            (output_index,) = output_indices
            pairs.update(
                ParentPair(output_index=output_index, input_index=input_index)
                for input_index in input_indices
            )
            continue
        requests.append(
            LocateRequest(
                input_indices=tuple(input_indices),
                output_indices=tuple(output_indices),
            )
        )

    if requests:
        pairs.update(_located_pairs(requests=requests, locator=locator))

    matched = {pair.input_index for pair in pairs}
    unmatched = tuple(
        sorted(
            input_index
            for input_indices in inputs_by_key.values()
            for input_index in input_indices
            if input_index not in matched
        )
    )
    return ParentsResolution(
        pairs=tuple(sorted(pairs)), unmatched_input_indices=unmatched
    )


def _group_by_key(
    *, rows: Iterable[tuple[int, DissolveKey]], side: str
) -> dict[DissolveKey, list[int]]:
    grouped: dict[DissolveKey, list[int]] = {}
    seen: set[int] = set()
    for index, key in rows:
        if index in seen:
            raise KeyMismatchError(f"{side} index {index} appears more than once")
        seen.add(index)
        grouped.setdefault(key, []).append(index)
    return grouped


def _located_pairs(
    *, requests: Sequence[LocateRequest], locator: PartLocator
) -> set[ParentPair]:
    """Call the locator once and reject any pair that crosses a key.

    Memory is O(inputs + outputs): one ordinal per input and one output set per
    request. An earlier version kept one output set per input, which is inputs x
    outputs and ran out of memory on a real 112,331-row key with 96,185 parts.
    """
    request_of_input: dict[int, int] = {}
    outputs_of_request: list[frozenset[int]] = []
    for ordinal, request in enumerate(requests):
        outputs_of_request.append(frozenset(request.output_indices))
        for input_index in request.input_indices:
            request_of_input[input_index] = ordinal

    located: set[ParentPair] = set()
    for pair in locator.locate(requests=requests):
        ordinal = request_of_input.get(pair.input_index)
        if ordinal is None:
            raise LocatorContractError(
                f"locator paired input {pair.input_index}, which was not in any request"
            )
        if pair.output_index not in outputs_of_request[ordinal]:
            raise LocatorContractError(
                f"locator paired input {pair.input_index} with output "
                f"{pair.output_index}, which is not a part of that input's key; "
                "the locator is not filtering by key"
            )
        located.add(pair)
    return located
