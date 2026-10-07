"""The driven-port Protocols and the values that cross them.

One flat module per port Protocol, plus the value types, predicates, row-shape grammar,
column constants, capability record and port errors. Membership test: it is a Protocol a
second adapter could implement, or a value named in a Protocol signature. It imports
only `ag.core.handles`, `ag.core.types`, `ag.core.injection` and `ag.core.errors`.

The re-export below is the operation-facing vocabulary, so an operation module opens with
one import rather than five. It is deliberately not everything: the Protocols are absent,
because an adapter's conformance assignment reads better naming the module it implements,
and leaving them out keeps the import at the head of an operation module a statement of
what operations are allowed to know. `NOT_INJECTED` is present because it appears in
operation definitions as the default for `tb`, exactly as `INJECTED` does for `scratch`.
The list is rebuilt as the surface lands.
"""

from ag.ports.attributes import AttributeValue as AttributeValue
from ag.ports.attributes import Field as Field
from ag.ports.attributes import FieldName as FieldName
from ag.ports.attributes import FieldType as FieldType
from ag.ports.geometry import CRS as CRS
from ag.ports.geometry import Coordinate as Coordinate
from ag.ports.geometry import Geometry as Geometry
from ag.ports.geometry import GeometryKind as GeometryKind
from ag.ports.geometry import Ring as Ring
from ag.ports.predicates import And as And
from ag.ports.predicates import Attr as Attr
from ag.ports.predicates import AttributeLeaf as AttributeLeaf
from ag.ports.predicates import Compare as Compare
from ag.ports.predicates import Comparison as Comparison
from ag.ports.predicates import DWithin as DWithin
from ag.ports.predicates import Intersects as Intersects
from ag.ports.predicates import IsIn as IsIn
from ag.ports.predicates import IsNull as IsNull
from ag.ports.predicates import Not as Not
from ag.ports.predicates import Or as Or
from ag.ports.predicates import Predicate as Predicate
from ag.ports.predicates import RawAttr as RawAttr
from ag.ports.predicates import Relation as Relation
from ag.ports.predicates import Spatial as Spatial
from ag.ports.predicates import Within as Within
from ag.ports.table_ops import Row as Row
from ag.ports.table_ops import Schema as Schema
from ag.ports.toolbox import NOT_INJECTED as NOT_INJECTED
from ag.ports.toolbox import Toolbox as Toolbox

__all__ = [
    "CRS",
    "NOT_INJECTED",
    "And",
    "Attr",
    "AttributeLeaf",
    "AttributeValue",
    "Compare",
    "Comparison",
    "Coordinate",
    "DWithin",
    "Field",
    "FieldName",
    "FieldType",
    "Geometry",
    "GeometryKind",
    "Intersects",
    "IsIn",
    "IsNull",
    "Not",
    "Or",
    "Predicate",
    "RawAttr",
    "Relation",
    "Ring",
    "Row",
    "Schema",
    "Spatial",
    "Toolbox",
    "Within",
]
