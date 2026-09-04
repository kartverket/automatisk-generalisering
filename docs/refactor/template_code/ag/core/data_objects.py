"""TEMPLATE — not shipped. Target module: `src/ag/core/data_objects.py`.

The data object model: the three things a stage can name, and lineage.

THREE KINDS OF THING

    ExternalSource   data entering the project from outside it. Declares location
                     and legality. Lives in sources.py, declared once.
    ProductIdentity  a published identity: something a pipeline produces and other
                     pipelines read. Declares location. Lives in products.py,
                     declared once.
    Derived          a new object produced by a stage. Has no location, ever.

WHY SOURCE AND PRODUCT ARE DIFFERENT TYPES

Under the old model both were `Source`, distinguished only by whether some pipeline
happened to publish the same (scale, dataset) pair. That made three things awkward
that are now trivial: a product had nowhere to declare its own location, an external
source had no required legality, and the link between producer and consumer was a
string match rather than a symbol.

Splitting them also makes the asymmetry explicit. An ExternalSource carries a
CLASSIFICATION, because its legality is a fact about data we did not make. A
ProductIdentity carries NONE, because the legality of something we produce is
computed over the stage wiring that produced it - and the single human assertion
that generalization removed a restriction has exactly one home, `reclassify_to` on a
Publish. A classification field here would give that judgement a second, unreviewed
home.

ALL THREE ARE SYMBOLS - eq=False

Identity equality, not value equality. Two separately written declarations of the
same dataset are two different objects, and that is now a non-issue rather than a
hazard, because there is only ever one declaration: sources.py and products.py are
the single site for each. `check_sources_agree` existed to reconcile independent
re-declarations and is gone with them.

Go-to-definition on an input lands on the declaration; find-references on
`N100_ROAD` answers "who produces this and who reads it" in one query.

ORIGIN IS ROOTS ONLY, AND IT MEANS LINEAGE - NOT INFLUENCE

`origin` answers "what dataset IS this, fundamentally". It names ExternalSources and
ProductIdentities and nothing else, so the chain does not have to be walked and
intermediate objects do not accumulate ancestry:

    SELECTED   = Derived("selected_polygons",   origin=(BUILDING_N50,))
    SIMPLIFIED = Derived("simplified_polygons", origin=(BUILDING_N50,))
    DISPLACED  = Derived("displaced_polygons",  origin=(BUILDING_N50,))

All three are building data. Displacement moved them using road geometry, but no
road data was merged into them, so ROAD stays out of their origin. Most objects have
exactly ONE origin and keep it for their whole life. Multiple origins appear when
data is genuinely combined - a join or a merge:

    ADDRESSED = Derived("addressed_buildings", origin=(BUILDING_N50, MATRIKKEL))

WHAT IS *NOT* DECLARED: THE IMMEDIATE PREDECESSOR

SIMPLIFIED comes from SELECTED, but that is not written anywhere. It is fully
determined by the operation wiring - the operation producing SIMPLIFIED takes
SELECTED as input. Declaring it again would be the same redundant-second-artifact
mistake as declaring dependency edges: more maintenance, another place for human
error, and no information gained.

So: origin is declared because it carries a human judgement nothing else knows.
Immediate lineage is derived because the wiring already states it.

LEGALITY IS *NOT* COMPUTED FROM ORIGIN

This is the important consequence of narrowing origin to lineage. If classification
were the join over `origin`, DISPLACED would come out CLOUD_OK - its origin is only
BUILDING_N50 - even though its geometry was determined by restricted NVDB_Roads
positions. Displaced building footprints partially encode the road centrelines they
were pushed away from, which is a real inference channel, not a theoretical one.

So classification is computed over the STAGE WIRING instead: every root that reached
a stage taints everything that stage produces, context included. See
policy.classification_of. Lineage and legality are two different traversals, and
this is exactly where they diverge.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias

from ag.core.types import Classification, DataType, DatasetName, Location, Scale


@dataclass(frozen=True, eq=False)
class ExternalSource:
    """Data entering the project from outside it. Declared once, in sources.py.

    IDENTITY equality. There is one declaration per dataset, so there is nothing to
    reconcile and no reason for two objects to compare equal.

    `classification` IS REQUIRED. It used to default to None, which made omission
    the path of least resistance - and combined with the old value equality on
    (scale, dataset), a second declaration that omitted it compared equal to one
    that said PREM_ONLY, so a pipeline reading the omitting declaration computed
    CLOUD_OK for restricted data and scheduled itself into the cloud with no error
    anywhere. A new restricted source now fails at import until someone states its
    legality, and appears as a diff in one reviewable file.
    """

    dataset: DatasetName
    scale: Scale
    location: Location
    classification: Classification
    data_type: DataType = DataType.FEATURE_CLASS

    def __repr__(self) -> str:
        return f"ExternalSource({self.scale}/{self.dataset})"


@dataclass(frozen=True, eq=False)
class ProductIdentity:
    """A published identity. Declared once, in products.py.

    THE SYMBOL BOTH SIDES REFERENCE:

        Publish(obj=ROAD, identity=N100_ROAD, reclassify_to=...)   the producer
        StageInput(obj=N100_ROAD, handle=..., role=...)            a consumer

    That is what closes the gap the old model recorded: `Publish` named a dataset
    but not a location, so a product's destination was written down by its CONSUMER
    (in that pipeline's Source declaration), and a product nobody consumed had no
    location anywhere. Here the location belongs to the identity, and exists whether
    or not anything reads it.

    It also turns `identity_producer` from a (scale, dataset) string match into a
    lookup keyed on the object itself.

    NO `classification` FIELD, deliberately. See the module docstring.
    """

    scale: Scale
    dataset: DatasetName
    location: Location
    data_type: DataType = DataType.FEATURE_CLASS

    def __repr__(self) -> str:
        return f"ProductIdentity({self.scale}/{self.dataset})"


LineageRoot: TypeAlias = ExternalSource | ProductIdentity
"""What an object can fundamentally BE. The two things that carry a location."""


@dataclass(frozen=True, eq=False)
class Derived:
    """A data object produced by a stage.

    IDENTITY equality (eq=False). These are symbols: two separately written
    Derived("selected", origin=(X,)) are different objects even if they look
    identical.

    THERE IS NO `location` PARAMETER, deliberately. A derived object cannot carry
    one. "A new identity must declare its location; an existing one inherits it" is
    enforced by construction rather than by a check - there is no way to express the
    wrong thing.

    `origin` names LINEAGE ROOTS ONLY - what dataset this fundamentally is. Usually
    one, stable for the object's whole life. More than one only when data is
    genuinely combined. It drives IDENTITY, not legality; see the module docstring.

    THE `name` STRING IS DELIBERATE AND STAYS A LITERAL. It is declared in exactly
    one place and no consumer anywhere requires it to match the symbol it is bound
    to: `SELECTED_ROADS = Derived("selected_roads", ...)` would work identically as
    `Derived("anything_unique", ...)`. By the identifier-versus-value test in
    operations.py it is a value, so it is NOT converted to a class body and there is
    NO symbol-versus-literal check.

    What IS required is uniqueness within the pipeline, because
    planning.scratch_location builds a remote path from it - and that is a check
    (validation.check_derived_names_unique), not a naming mechanism.

    Converting it would also have a cost nothing else here has: the name is part of
    a run-scratch path, so an LSP rename would move a live object's location and
    invalidate the resume window for any in-flight run. Leave it alone.
    """

    name: str
    origin: tuple[LineageRoot, ...]
    data_type: DataType = DataType.FEATURE_CLASS

    def __repr__(self) -> str:
        return f"Derived({self.name!r})"


DataObject: TypeAlias = ExternalSource | ProductIdentity | Derived
"""Anything a StageInput may name. A StageOutput may only name a Derived."""


def lineage_roots(obj: DataObject) -> tuple[LineageRoot, ...]:
    """The roots an object belongs to. No recursion needed - origin is already
    roots only, which is the point of narrowing it."""
    return obj.origin if isinstance(obj, Derived) else (obj,)
