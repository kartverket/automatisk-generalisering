"""The two members of `types` that carry logic: the scale order and the classification
lattice.

What: `Scale.rank` orders the scales finest to coarsest with `RAW` finest, whatever the
members' text order; `Classification.join` fails closed over every pair of members.
"""

from __future__ import annotations

from itertools import product

from ag.core.types import Classification, Scale

FINEST_TO_COARSEST = (
    Scale.RAW,
    Scale.N10,
    Scale.N25,
    Scale.N50,
    Scale.N100,
    Scale.N250,
)


def test_rank_orders_every_scale_finest_to_coarsest() -> None:
    assert tuple(sorted(Scale, key=lambda scale: scale.rank)) == FINEST_TO_COARSEST
    ranks = [scale.rank for scale in FINEST_TO_COARSEST]
    assert ranks == sorted(set(ranks))
    assert Scale.RAW.rank == 0


def test_every_member_has_a_rank_and_definition_order_is_rank_order() -> None:
    """A member added without a rank entry would fail only when first read; here it
    fails at once, and the members stay listed finest to coarsest."""
    ranks = [scale.rank for scale in Scale]
    assert ranks == sorted(ranks)
    assert len(set(ranks)) == len(ranks)


def test_rank_is_what_text_order_is_not() -> None:
    """Documents the `StrEnum` hazard that `rank` exists for: members compare as text.
    If `Scale` ever defines rank-based ordering, delete this test rather than fix it."""
    assert Scale.N25 > Scale.N100
    assert Scale.N25.rank < Scale.N100.rank


def test_the_scale_literals_are_the_storage_spelling() -> None:
    assert [scale.value for scale in Scale] == [
        "raw",
        "n10",
        "n25",
        "n50",
        "n100",
        "n250",
    ]
    assert f"{Scale.N100}" == "n100"


CLOUD_OK = Classification.CLOUD_OK
PREM_ONLY = Classification.PREM_ONLY


def test_join_truth_table() -> None:
    """Stated case by case, so a new member forces a decision here."""
    assert CLOUD_OK.join(CLOUD_OK) is CLOUD_OK
    assert CLOUD_OK.join(PREM_ONLY) is PREM_ONLY
    assert PREM_ONLY.join(CLOUD_OK) is PREM_ONLY
    assert PREM_ONLY.join(PREM_ONLY) is PREM_ONLY
    assert len(Classification) == 2


def test_join_is_symmetric_over_every_pair() -> None:
    for left, right in product(Classification, repeat=2):
        assert left.join(right) is right.join(left), (left, right)


def test_permits_truth_table() -> None:
    """Cloud data may be stored anywhere; on-prem data only on-prem."""
    assert CLOUD_OK.permits(CLOUD_OK)
    assert CLOUD_OK.permits(PREM_ONLY)
    assert not PREM_ONLY.permits(CLOUD_OK)
    assert PREM_ONLY.permits(PREM_ONLY)


def test_every_classification_permits_its_own_storage() -> None:
    """Reflexivity: data is always storable under its own classification. A member
    `join` has not been taught about fails here, which is the tripwire."""
    for member in Classification:
        assert member.permits(member), member
