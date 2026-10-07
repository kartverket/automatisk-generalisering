"""Names and enums shared across the planning layer.

What: the string aliases for the open-ended names, and the closed sets the system
reasons over: scales, objects, data types, input roles, classification, environment and
storage scope.

Why: the aliases are `TypeAlias` rather than `NewType` because every one of them is a
string at every boundary (configuration, object storage keys, job labels) and `NewType`
would mean a cast at each; the alias earns its place by naming the domain concept. Nothing
here depends on anything else in this package.
"""

from __future__ import annotations

from collections.abc import Mapping
from enum import Enum, StrEnum
from typing import TypeAlias

DatasetName: TypeAlias = str
"""A registry identity such as `"Road"` or `"BuildingPolygons"`."""

StageName: TypeAlias = str
OperationName: TypeAlias = str

ParamName: TypeAlias = str
"""A keyword name in an operation function's signature."""

Location: TypeAlias = str
"""A storage URI for a remote scope; the scheme selects the archive client.

Today `"s3://bucket/path"` for the on-prem object store and `"gs://bucket/path"` in
cloud; a shared filesystem, if the platform offers one, is another scheme and another
client. Pod-local paths are carried by materialised handles, never by locations.
"""

RunId: TypeAlias = str


class Scale(StrEnum):
    """The cartographic scales, plus `RAW` for data that has none.

    Why: a closed set, not a string. A scale reaches four independent path builders, the
    coarser-feeds-finer check, run selection, and the identity another pipeline resolves
    against; a typo in any one of those is a stage that silently matches nothing or a
    path that silently diverges. `StrEnum` so a member renders as its value in an f-string
    and a path join; with a plain `Enum` the one path builder that forgets `.value`
    produces `Scale.N100` inside a bucket key. The literals stay explicit because they
    cross a boundary into storage paths and product names.

    Compare scales by `rank`, never by `<` on members: a `StrEnum` orders as text, where
    `"n25"` sorts after `"n100"`.

    `RAW` is source data with no cartographic scale. Identity is (scale, dataset), and a
    registry keyed on a sometimes-absent field is worse than one with an explicit
    sentinel. `RAW` ranks finest so anything may read it, and `RAW` identities have no
    producer, so the one-producer rule is vacuous for them.
    """

    RAW = "raw"
    N10 = "n10"
    N25 = "n25"
    N50 = "n50"
    N100 = "n100"
    N250 = "n250"

    @property
    def rank(self) -> int:
        """Position from finest to coarsest: the denominator in thousands, `RAW` zero."""
        return _SCALE_RANK[self]


_SCALE_RANK: Mapping[Scale, int] = {
    Scale.RAW: 0,
    Scale.N10: 10,
    Scale.N25: 25,
    Scale.N50: 50,
    Scale.N100: 100,
    Scale.N250: 250,
}


class ObjectName(StrEnum):
    """The pipeline domains.

    Why: a closed set means adding an object edits a shared module, and that is the
    intended trade at this scale. There are single digits of these, they change once a
    year, and every one appears in a path, a job label and a run selector; an open string
    buys nothing but the chance to misspell one.
    """

    ROAD = "road"
    BUILDING = "building"
    RIVER = "river"
    RAILWAY = "railway"
    LAND_USE = "land_use"


PipelineKey: TypeAlias = tuple[Scale, ObjectName]


class DataType(Enum):
    """What kind of dataset a handle names."""

    FEATURE_CLASS = "feature_class"
    TABLE = "table"
    RASTER = "raster"


class InputRole(Enum):
    """How fan-out treats a stage input.

    `PROCESSING` inputs determine partition extents and drive fan-in: centre-in features
    are kept, the rest discarded. `CONTEXT` inputs are selected within the halo radius to
    inform the operation and are not carried into the output. A non-spatial lookup table
    is `CONTEXT` in the operative sense: replicated to every pod, not partitioned, not in
    the output.

    Why: declared for fan-out's benefit, not the operation's. An operation never learns
    which of its inputs was partitioned.
    """

    PROCESSING = "processing"
    CONTEXT = "context"


class Classification(Enum):
    """Where an output may be stored.

    Determined by policy, not by where the data currently sits, and independent of the
    URI scheme.
    """

    CLOUD_OK = "cloud_ok"
    PREM_ONLY = "prem_only"

    def join(self, other: Classification) -> Classification:
        """The most restrictive of the two.

        Why: `CLOUD_OK` only when both operands are `CLOUD_OK`, so a member added later
        is treated as restricted until this method is taught otherwise. Fails closed.
        """
        if self is Classification.CLOUD_OK and other is Classification.CLOUD_OK:
            return Classification.CLOUD_OK
        return Classification.PREM_ONLY

    def permits(self, storage: Classification) -> bool:
        """Whether data of this classification may be stored where `storage` applies."""
        return self.join(storage) is storage


class Environment(Enum):
    """Where pods run. Determined by reachability, not by classification."""

    ON_PREM = "on_prem"
    ON_CLOUD = "on_cloud"


class StorageScope(Enum):
    """Which namespace an edge crosses. Derived from stage tags, never declared.

    Why: the substrate behind each scope is a deployment choice, not a model choice.
    `POD_LOCAL` is always the pod's own ephemeral disk. `INTRA_STAGE` (fan-out to
    workers to fan-in) and `RUN_SCRATCH` (stage to stage within one pipeline) are object
    storage today and a shared filesystem if the platform offers one. `ARCHIVE` (pipeline
    to pipeline) is always object storage and always durable. Keeping the substrate out of
    the model is what makes a filesystem swap an adapter change rather than a redesign.
    """

    POD_LOCAL = "pod_local"
    INTRA_STAGE = "intra_stage"
    RUN_SCRATCH = "run_scratch"
    ARCHIVE = "archive"
