"""TEMPLATE — not shipped. Target module: `src/ag/core/types.py`.

Names and enums shared across the planning layer.

Nothing here depends on anything else in this package.
"""

from __future__ import annotations

from enum import Enum, StrEnum
from typing import TypeAlias

# ---------------------------------------------------------------------------
# TypeAlias rather than NewType for the open-ended strings: these are all strings
# at every boundary (config files, object storage keys, Job labels), and NewType
# would mean casting at each one. The alias earns its place by naming the domain
# concept.
# ---------------------------------------------------------------------------

DatasetName: TypeAlias = str  # "Road", "BuildingPolygons" - a registry identity
StageName: TypeAlias = str
OperationName: TypeAlias = str
ParamName: TypeAlias = str  # keyword name in an operation function signature
Location: TypeAlias = str  # "gs://bucket/path" or "s3://bucket/path"
RunId: TypeAlias = str


class Scale(StrEnum):
    """The cartographic scales, plus RAW for data that has none.

    CLOSED SET, not a string. Scale reaches four independent path builders, the
    coarser-feeds-finer check, run selection, and the identity another pipeline
    resolves against. A typo in any one of those is a stage that silently matches
    nothing or a path that silently diverges.

    StrEnum rather than Enum so a member renders as its value in an f-string and a
    path join. With a plain Enum every path builder has to remember `.value`, and
    the one that forgets produces `Scale.N100` inside a bucket key.

    THE LITERALS STAY EXPLICIT. These values cross a boundary - they appear in
    object storage paths and in published product names - so they are values, and
    the enum names them rather than replacing them.

    RAW is source data with no cartographic scale: NVDB_Roads, Matrikkel and
    similar. Identity is (scale, dataset), and a registry keyed on a
    sometimes-absent field is worse than one with an explicit sentinel. Two
    consequences: the coarser-feeds-finer check must rank RAW as finest so anything
    may read it, and RAW identities have no producer, so the one-producer rule is
    vacuous for them rather than violated.
    """

    RAW = "raw"
    N10 = "n10"
    N25 = "n25"
    N50 = "n50"
    N100 = "n100"
    N250 = "n250"


class ObjectName(StrEnum):
    """The pipeline domains.

    A CLOSED SET MEANS ADDING AN OBJECT EDITS A SHARED MODULE. That is the intended
    tradeoff at this scale: there are single digits of these, they change once a
    year, and every one of them appears in a path, a Job label and a run selector.
    An open string buys nothing here except the chance to misspell one.
    """

    ROAD = "road"
    BUILDING = "building"
    RIVER = "river"
    RAILWAY = "railway"
    LAND_USE = "land_use"


PipelineKey: TypeAlias = tuple[Scale, ObjectName]


class DataType(Enum):
    FEATURE_CLASS = "feature_class"
    TABLE = "table"
    RASTER = "raster"


class InputRole(Enum):
    """PROCESSING inputs determine partition extents and drive fan-in: center-in
    features are kept, the rest discarded. CONTEXT inputs are selected within the
    halo radius to inform the operation and are not carried into the output.

    A non-spatial lookup table is CONTEXT in the operative sense - replicated to
    every pod, not partitioned, not in the output - so the binary is sufficient.

    Note this is declared for the FAN-OUT's benefit, not the operation's. An
    operation never learns which of its inputs was partitioned.
    """

    PROCESSING = "processing"
    CONTEXT = "context"


class Classification(Enum):
    """Where an output MAY be stored. Determined by policy, not by where it
    currently sits, and explicitly independent of URI scheme."""

    CLOUD_OK = "cloud_ok"
    PREM_ONLY = "prem_only"

    def join(self, other: Classification) -> Classification:
        """Most restrictive wins. Fails closed."""
        if self is Classification.PREM_ONLY or other is Classification.PREM_ONLY:
            return Classification.PREM_ONLY
        return Classification.CLOUD_OK

    def permits(self, other: Classification) -> bool:
        return self.join(other) is other


class Environment(Enum):
    """Where pods run. Determined by REACHABILITY, not by classification."""

    ON_PREM = "on_prem"
    ON_CLOUD = "on_cloud"


class StorageScope(Enum):
    """Which namespace an edge crosses. DERIVED from stage tags, never declared.

    The SUBSTRATE behind each scope is a deployment choice, not a model choice:

        POD_LOCAL    always the pod's own /tmp (emptyDir).
        INTRA_STAGE  fan-out -> workers -> fan-in. Object storage today; shared
                     NFS if the platform offers ReadWriteMany. See staging.py.
        RUN_SCRATCH  stage -> stage within one pipeline. Same choice as above.
        ARCHIVE      pipeline -> pipeline. Always object storage, always durable.

    Keeping substrate out of the model is what makes an NFS swap an adapter change
    rather than a redesign.
    """

    POD_LOCAL = "pod_local"
    INTRA_STAGE = "intra_stage"
    RUN_SCRATCH = "run_scratch"
    ARCHIVE = "archive"
