"""TEMPLATE — not shipped. Target module: `src/ag/classification_rules.py`.

The whole classification policy, in one file, so a security reviewer can read it
without reading any pipeline — 02-runtime §5.4.

MOST SPECIFIC FIRST. A rule keys on VALUES, a scale and a dataset name, deliberately:
it is written against a policy document rather than against this codebase's symbols,
and it must be able to name a dataset that has no declaration here yet.

An over-broad rule costs invisibly. Nothing errors; work simply runs on-prem forever
and outputs inherit restrictions they never needed. Fail-closed is the right default,
but check each rule against what is genuinely restricted rather than adopting it as a
conservative guess.
"""

from __future__ import annotations

from ag.core.policy import ClassificationRule
from ag.core.types import Classification, Scale

RULES: tuple[ClassificationRule, ...] = (
    ClassificationRule(
        scale=None, dataset="NVDB_Roads", gives=Classification.PREM_ONLY
    ),
    ClassificationRule(scale=Scale.N10, dataset=None, gives=Classification.PREM_ONLY),
    ClassificationRule(scale=None, dataset=None, gives=Classification.CLOUD_OK),
)
"""The catch-all last is what stops everything failing closed. Without it an unlisted
dataset is PREM_ONLY — the correct default, but it would make every example print
nothing but prem_only."""
