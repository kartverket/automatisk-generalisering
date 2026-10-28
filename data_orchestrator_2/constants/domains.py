# Libraries

from collections import defaultdict
from dataclasses import dataclass
from enum import Flag, auto

from data_orchestrator_2.schemas.fields import ColumnName

###############################
# Classes
###############################


class DomainScale(Flag):
    """Flags indicating at which scale a field value is valid."""

    N10 = auto()
    N25 = auto()
    N50 = auto()
    N100 = auto()
    N250 = auto()
    N500 = auto()


class DomainObject(Flag):
    """Flags indicating which objects a field value is valid for."""

    ELVEG_AND_STI = auto()
    VEGSPERRING = auto()


@dataclass(frozen=True, slots=True)
class DomainValue:
    """Metadata for allowed field values."""

    value: str
    column: ColumnName
    scales: DomainScale
    objects: DomainObject


###############################
# Actual allowed values
###############################


""" Which values are allowed for field [...] """

FIELD_VALUE_CATALOG = frozenset(
    [
        DomainValue(
            value="NEI",
            column=ColumnName.KONNEKTERINGSLENKE,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
        ),
        DomainValue(
            value="JA",
            column=ColumnName.KONNEKTERINGSLENKE,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
        ),
        # https://register.geonorge.no/sosi-kodelister/kartdata/mediumsamferdsel
        DomainValue(
            value="B",
            column=ColumnName.MEDIUM,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
        ),
        DomainValue(
            value="L",
            column=ColumnName.MEDIUM,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
        ),
        DomainValue(
            value="T",
            column=ColumnName.MEDIUM,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
        ),
        DomainValue(
            value="U",
            column=ColumnName.MEDIUM,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
        ),
        # https://register.geonorge.no/sosi-kodelister/kartdata/motorvegtype
        DomainValue(
            value="IkkeMotorveg",
            column=ColumnName.MOTORVEGTYPE,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
        ),
        DomainValue(
            value="motortrafikkveg",
            column=ColumnName.MOTORVEGTYPE,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
        ),
        DomainValue(
            value="motorveg",
            column=ColumnName.MOTORVEGTYPE,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
        ),
        DomainValue(
            value="Udefinert",
            column=ColumnName.MOTORVEGTYPE,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
        ),
        DomainValue(
            value="Barmarksløype",
            column=ColumnName.OBJTYPE,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
        ),
        DomainValue(
            value="GangSykkelveg",
            column=ColumnName.OBJTYPE,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
        ),
        DomainValue(
            value="Sti",
            column=ColumnName.OBJTYPE,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
        ),
        DomainValue(
            value="Traktorveg",
            column=ColumnName.OBJTYPE,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
        ),
        DomainValue(
            value="VegSenterlinje",
            column=ColumnName.OBJTYPE,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
        ),
        # https://register.geonorge.no/sosi-kodelister/kartdata/rutemerking
        DomainValue(
            value="Nei",
            column=ColumnName.RUTEMERKING,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
        ),
        DomainValue(
            value="Ja",
            column=ColumnName.RUTEMERKING,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
        ),
        DomainValue(
            value="Udefinert",
            column=ColumnName.RUTEMERKING,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
        ),
        # https://register.geonorge.no/sosi-kodelister/kartdata/typeveg
        DomainValue(
            value="annet",
            column=ColumnName.TYPEVEG,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
        ),
        DomainValue(
            value="barmarksløype",
            column=ColumnName.TYPEVEG,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
        ),
        DomainValue(
            value="bilferje",
            column=ColumnName.TYPEVEG,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
        ),
        DomainValue(
            value="enkelBilveg",
            column=ColumnName.TYPEVEG,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
        ),
        DomainValue(
            value="gangOgSykkelveg",
            column=ColumnName.TYPEVEG,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
        ),
        DomainValue(
            value="gangveg",
            column=ColumnName.TYPEVEG,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
        ),
        DomainValue(
            value="kanalisertVeg",
            column=ColumnName.TYPEVEG,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
        ),
        DomainValue(
            value="passasjerferje",
            column=ColumnName.TYPEVEG,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
        ),
        DomainValue(
            value="rampe",
            column=ColumnName.TYPEVEG,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
        ),
        DomainValue(
            value="rundkjøring",
            column=ColumnName.TYPEVEG,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
        ),
        DomainValue(
            value="sti",
            column=ColumnName.TYPEVEG,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
        ),
        DomainValue(
            value="traktorveg",
            column=ColumnName.TYPEVEG,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
        ),
        # https://register.geonorge.no/sosi-kodelister/kartdata/vedlikeholdsansvarlig
        DomainValue(
            value="Andre",
            column=ColumnName.VEDLIKEH,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
        ),
        DomainValue(
            value="DNT",
            column=ColumnName.VEDLIKEH,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
        ),
        DomainValue(
            value="Ukjent",
            column=ColumnName.VEDLIKEH,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
        ),
        # https://register.geonorge.no/sosi-kodelister/kartdata/vegkategori
        DomainValue(
            value="E",
            column=ColumnName.VEGKATEGORI,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
        ),
        DomainValue(
            value="F",
            column=ColumnName.VEGKATEGORI,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
        ),
        DomainValue(
            value="K",
            column=ColumnName.VEGKATEGORI,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
        ),
        DomainValue(
            value="P",
            column=ColumnName.VEGKATEGORI,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
        ),
        DomainValue(
            value="R",
            column=ColumnName.VEGKATEGORI,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
        ),
    ]
)


_temp = defaultdict(set)

for domain_value in FIELD_VALUE_CATALOG:
    for scale in DomainScale:
        if not (domain_value.scales & scale):
            continue
        for obj in DomainObject:
            if domain_value.objects & obj:
                _temp[(domain_value.column, scale, obj)].add(domain_value.value)

DOMAIN_INDEX: dict[tuple[ColumnName, DomainScale, DomainObject], frozenset[str]] = {
    key: frozenset(value) for key, value in _temp.items()
}


def get_allowed_values(
    column: ColumnName, scale: DomainScale, obj: DomainObject
) -> frozenset[str]:
    return DOMAIN_INDEX.get((column, scale, obj), frozenset())
