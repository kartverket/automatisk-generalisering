"""TEMPLATE — not shipped. Target module: `src/ag/sources.py`.

Every external source in the project. One declaration each, nowhere else.

A LEAF MODULE. It imports core_types and data_objects and nothing else - never a
pipeline, never a generalization module. An import-linter contract enforces that
(see .importlinter); without it, one convenience import turns this into a cycle and
the "read one file and see everything entering the project" property is gone.

WHY THIS IS CENTRAL AND `products.py` IS TOO, WHEN NOTHING ELSE IN THIS DESIGN IS

The old model had each pipeline declare its own sources, with value equality on
(scale, dataset) linking independent declarations and `check_sources_agree`
reconciling them. That is a genuine leak, not a tidiness complaint:

    classification, location and data_type were all compare=False, so a second
    declaration of NVDB_Roads that omitted `classification` compared equal, hashed
    equal, and linked as the same identity. policy.classification_of joins over the
    sources reached by THAT pipeline's wiring, so the omitting pipeline computed
    CLOUD_OK for restricted data and scheduled itself into the cloud. No error
    anywhere - the check would have caught a location disagreement, and legality was
    not what it compared.

Making `classification` required kills the omission path. Making this the single
declaration site kills the disagreement path. Together they turn a class of silent
misclassification into a TypeError at import.

WHAT IS PRESERVED. No pipeline imports another pipeline. That property was the
reason for independent re-declaration, and it survives: pipelines import this leaf,
not each other.

WHAT BELONGS HERE. Only data the project does not produce. Anything a pipeline in
this project publishes is a ProductIdentity and belongs in products.py, even when a
consumer treats it as external input.
"""

from __future__ import annotations

from ag.core.types import Classification, DataType, Scale
from ag.core.data_objects import ExternalSource

# ---------------------------------------------------------------------------
# Restricted
# ---------------------------------------------------------------------------

NVDB_ROADS = ExternalSource(
    dataset="NVDB_Roads",
    scale=Scale.RAW,
    location="s3://kv-source/nvdb/roads.gdb",
    classification=Classification.PREM_ONLY,
)
"""Authoritative road source geometry.

Read as CONTEXT by road_n100's network stage and by building_n100's displacement
stage. Its s3:// location is why both pipelines run on-prem, and its PREM_ONLY
classification is why everything either stage produces is PREM_ONLY until a Publish
asserts otherwise.
"""


# ---------------------------------------------------------------------------
# Open
# ---------------------------------------------------------------------------

ADMIN_AREAS = ExternalSource(
    dataset="AdminAreas",
    scale=Scale.RAW,
    location="gs://kv-source/admin/areas.gdb",
    classification=Classification.CLOUD_OK,
    data_type=DataType.TABLE,
)
"""Municipality and county attributes. Non-spatial, so CONTEXT in the operative
sense: replicated whole to every pod, written once at a shared key rather than K
times."""

MATRIKKEL = ExternalSource(
    dataset="Matrikkel",
    scale=Scale.RAW,
    location="gs://kv-source/matrikkel/buildings.gdb",
    classification=Classification.CLOUD_OK,
)
"""The cadastre. Building attributes are joined from it, which is what makes
building_n100's addressed objects multi-origin."""

MUNICIPALITY_CODES = ExternalSource(
    dataset="MunicipalityCodes",
    scale=Scale.RAW,
    location="gs://kv-source/admin/municipality_codes.gdb",
    classification=Classification.CLOUD_OK,
    data_type=DataType.TABLE,
)
"""A small lookup table. Shows the unpartitioned-context transfer shape at its
cheapest: a few hundred rows written once and read by all K workers."""
