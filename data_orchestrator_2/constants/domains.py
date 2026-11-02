# Libraries

from collections import defaultdict
from dataclasses import dataclass
from enum import Flag, auto

import numpy as np

from data_orchestrator_2.constants.columns import ColumnName

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
    N1000 = auto()
    N2000 = auto()
    N5000 = auto()


class DomainObject(Flag):
    """Flags indicating which objects a field value is valid for."""

    ELVEG_AND_STI = auto()
    VEGSPERRING = auto()


@dataclass(frozen=True, slots=True)
class TypeValue:
    """Accepts any value of the given types; strings may be capped by max_length."""

    types: tuple[type, ...]
    max_length: int | None = None

    def __str__(self) -> str:
        types = ", ".join(t.__name__ for t in self.types)
        if self.max_length is None:
            return f"TypeValue(types={types})"
        return f"TypeValue(types={types}, max_length={self.max_length})"

    def matches(self, actual_value: str | int | float | None) -> bool:
        if (
            self.max_length is not None
            and str in self.types
            and isinstance(actual_value, str)
        ):
            return len(actual_value) <= self.max_length
        return isinstance(actual_value, self.types)


@dataclass(frozen=True, slots=True)
class RangeValue:
    min_value: int | float
    max_value: int | float

    def __str__(self) -> str:
        return f"RangeValue(min_value={self.min_value}, max_value={self.max_value})"

    def matches(self, actual_value: str | int | float | None) -> bool:
        return (
            isinstance(actual_value, (int, float))
            and self.min_value <= actual_value <= self.max_value
        )


@dataclass(frozen=True, slots=True)
class DomainValue:
    """Metadata for allowed field values."""

    value: str | None | TypeValue | RangeValue
    column: ColumnName
    scales: DomainScale
    objects: DomainObject

    def matches(self, actual_value: str | int | float | None) -> bool:
        if isinstance(self.value, (TypeValue, RangeValue)):
            return self.value.matches(actual_value)
        return self.value == actual_value


###############################
# Actual allowed values
###############################


""" Which values are allowed for field [...] """

FIELD_VALUE_CATALOG = frozenset(
    [
        # Adressenavn
        DomainValue(
            value=TypeValue(types=(str, type(None)), max_length=30),
            column=ColumnName.ADRESSENAVN,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
        ),
        # Adskiltelop
        DomainValue(
            value="med",
            column=ColumnName.ADSKILTELOP,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
        ),
        DomainValue(
            value="mot",
            column=ColumnName.ADSKILTELOP,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
        ),
        DomainValue(
            value=None,
            column=ColumnName.ADSKILTELOP,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
        ),
        # Adskiltelopnummer
        DomainValue(
            value=TypeValue(types=(str, type(None)), max_length=3),
            column=ColumnName.ADSKILTELOPNUMMER,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
        ),
        # Areal_m2
        DomainValue(
            value=RangeValue(min_value=0, max_value=np.inf),
            column=ColumnName.AREAL_M2,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
        ),
        # Eier
        DomainValue(
            value="fylkeskommune",
            column=ColumnName.EIER,
            scales=(DomainScale.N100),
            objects=(DomainObject.VEGSPERRING),
        ),
        DomainValue(
            value="kommune",
            column=ColumnName.EIER,
            scales=(DomainScale.N100),
            objects=(DomainObject.VEGSPERRING),
        ),
        DomainValue(
            value="NyeVeier",
            column=ColumnName.EIER,
            scales=(DomainScale.N100),
            objects=(DomainObject.VEGSPERRING),
        ),
        DomainValue(
            value="privat",
            column=ColumnName.EIER,
            scales=(DomainScale.N100),
            objects=(DomainObject.VEGSPERRING),
        ),
        DomainValue(
            value="StatensVegvesen",
            column=ColumnName.EIER,
            scales=(DomainScale.N100),
            objects=(DomainObject.VEGSPERRING),
        ),
        DomainValue(
            value="uavklart",
            column=ColumnName.EIER,
            scales=(DomainScale.N100),
            objects=(DomainObject.VEGSPERRING),
        ),
        DomainValue(
            value=None,
            column=ColumnName.EIER,
            scales=(DomainScale.N100),
            objects=(DomainObject.VEGSPERRING),
        ),
        # Feltoversikt
        DomainValue(
            value=TypeValue(types=(str, type(None)), max_length=50),
            column=ColumnName.FELTOVERSIKT,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
        ),
        # Funksjon
        DomainValue(
            value="betalingssperring",
            column=ColumnName.FUNKSJON,
            scales=(DomainScale.N100),
            objects=(DomainObject.VEGSPERRING),
        ),
        DomainValue(
            value="bussluse",
            column=ColumnName.FUNKSJON,
            scales=(DomainScale.N100),
            objects=(DomainObject.VEGSPERRING),
        ),
        DomainValue(
            value="fjernstyrtSperring",
            column=ColumnName.FUNKSJON,
            scales=(DomainScale.N100),
            objects=(DomainObject.VEGSPERRING),
        ),
        DomainValue(
            value="låstSperring",
            column=ColumnName.FUNKSJON,
            scales=(DomainScale.N100),
            objects=(DomainObject.VEGSPERRING),
        ),
        DomainValue(
            value="trafikkavviser",
            column=ColumnName.FUNKSJON,
            scales=(DomainScale.N100),
            objects=(DomainObject.VEGSPERRING),
        ),
        DomainValue(
            value="ulåstSperring",
            column=ColumnName.FUNKSJON,
            scales=(DomainScale.N100),
            objects=(DomainObject.VEGSPERRING),
        ),
        # Konnekteringslenke
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
        DomainValue(
            value=None,
            column=ColumnName.KONNEKTERINGSLENKE,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
        ),
        # Kryssdel
        DomainValue(
            value=None,
            column=ColumnName.KRYSSDEL,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
        ),
        DomainValue(
            value=RangeValue(min_value=1, max_value=14),
            column=ColumnName.KRYSSDEL,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
        ),
        # Medium
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
        # Motorvegtype
        DomainValue(
            value="Ikke motorveg",
            column=ColumnName.MOTORVEGTYPE,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
        ),
        DomainValue(
            value="Motortrafikkveg",
            column=ColumnName.MOTORVEGTYPE,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
        ),
        DomainValue(
            value="Motorveg",
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
        # Objtype
        DomainValue(
            value="Barmarksløype",
            column=ColumnName.OBJTYPE,
            scales=(DomainScale.N50 | DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
        ),
        DomainValue(
            value="GangSykkelveg",
            column=ColumnName.OBJTYPE,
            scales=(DomainScale.N50 | DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
        ),
        DomainValue(
            value="Sti",
            column=ColumnName.OBJTYPE,
            scales=(
                DomainScale.N50
                | DomainScale.N100
                | DomainScale.N250
                | DomainScale.N500
                | DomainScale.N1000
            ),
            objects=(DomainObject.ELVEG_AND_STI),
        ),
        DomainValue(
            value="Traktorveg",
            column=ColumnName.OBJTYPE,
            scales=(
                DomainScale.N50
                | DomainScale.N100
                | DomainScale.N250
                | DomainScale.N500
                | DomainScale.N1000
            ),
            objects=(DomainObject.ELVEG_AND_STI),
        ),
        DomainValue(
            value="VegSenterlinje",
            column=ColumnName.OBJTYPE,
            scales=(
                DomainScale.N50
                | DomainScale.N100
                | DomainScale.N250
                | DomainScale.N500
                | DomainScale.N1000
                | DomainScale.N2000
                | DomainScale.N5000
            ),
            objects=(DomainObject.ELVEG_AND_STI),
        ),
        DomainValue(
            value="Vegsperring",
            column=ColumnName.OBJTYPE,
            scales=(DomainScale.N100),
            objects=(DomainObject.VEGSPERRING),
        ),
        # Rutemerking
        DomainValue(
            value="NEI",
            column=ColumnName.RUTEMERKING,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
        ),
        DomainValue(
            value="JA",
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
        DomainValue(
            value=None,
            column=ColumnName.RUTEMERKING,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
        ),
        # Sideanleggsdel
        DomainValue(
            value=RangeValue(min_value=1, max_value=6),
            column=ColumnName.SIDEANLEGGSDEL,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
        ),
        DomainValue(
            value=None,
            column=ColumnName.SIDEANLEGGSDEL,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
        ),
        # Subtypekode
        DomainValue(
            value=TypeValue(types=(str,), max_length=200),
            column=ColumnName.SUBTYPEKODE,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
        ),
        # Type
        DomainValue(
            value="betongkjegle",
            column=ColumnName.TYPE,
            scales=(DomainScale.N100),
            objects=(DomainObject.VEGSPERRING),
        ),
        DomainValue(
            value="bilsperre",
            column=ColumnName.TYPE,
            scales=(DomainScale.N100),
            objects=(DomainObject.VEGSPERRING),
        ),
        DomainValue(
            value="bomMedAutomatiskÅpner",
            column=ColumnName.TYPE,
            scales=(DomainScale.N100),
            objects=(DomainObject.VEGSPERRING),
        ),
        DomainValue(
            value="bussluse",
            column=ColumnName.TYPE,
            scales=(DomainScale.N100),
            objects=(DomainObject.VEGSPERRING),
        ),
        DomainValue(
            value="låstBom",
            column=ColumnName.TYPE,
            scales=(DomainScale.N100),
            objects=(DomainObject.VEGSPERRING),
        ),
        DomainValue(
            value="newJersey",
            column=ColumnName.TYPE,
            scales=(DomainScale.N100),
            objects=(DomainObject.VEGSPERRING),
        ),
        DomainValue(
            value="rørgelender",
            column=ColumnName.TYPE,
            scales=(DomainScale.N100),
            objects=(DomainObject.VEGSPERRING),
        ),
        DomainValue(
            value="steinblokk",
            column=ColumnName.TYPE,
            scales=(DomainScale.N100),
            objects=(DomainObject.VEGSPERRING),
        ),
        DomainValue(
            value="trafikkavviser",
            column=ColumnName.TYPE,
            scales=(DomainScale.N100),
            objects=(DomainObject.VEGSPERRING),
        ),
        DomainValue(
            value=None,
            column=ColumnName.TYPE,
            scales=(DomainScale.N100),
            objects=(DomainObject.VEGSPERRING),
        ),
        # Typeveg
        DomainValue(
            value="Barmarksløype",
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
            value="Gang- og Sykkelveg",
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
            value="Privat Veg",
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
            value="Sti DNT",
            column=ColumnName.TYPEVEG,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
        ),
        DomainValue(
            value="Sti ikke merket",
            column=ColumnName.TYPEVEG,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
        ),
        DomainValue(
            value="Sti merket",
            column=ColumnName.TYPEVEG,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
        ),
        DomainValue(
            value="Traktorveg",
            column=ColumnName.TYPEVEG,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
        ),
        # Uttegning
        DomainValue(
            value="1 vinge",
            column=ColumnName.UTTEGNING,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
        ),
        DomainValue(
            value=None,
            column=ColumnName.UTTEGNING,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
        ),
        # Vedlikeh
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
            value="Udefinert",
            column=ColumnName.VEDLIKEH,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
        ),
        DomainValue(
            value=None,
            column=ColumnName.VEDLIKEH,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
        ),
        # Vegkategori
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
        DomainValue(
            value="S",
            column=ColumnName.VEGKATEGORI,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
        ),
        DomainValue(
            value=None,
            column=ColumnName.VEGKATEGORI,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
        ),
        # Vegklasse
        DomainValue(
            value=RangeValue(min_value=1, max_value=9),
            column=ColumnName.VEGKLASSE,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
        ),
        DomainValue(
            value=None,
            column=ColumnName.VEGKLASSE,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
        ),
        # Vegnummer
        DomainValue(
            value=TypeValue(types=(int, float)),
            column=ColumnName.VEGNUMMER,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
        ),
        DomainValue(
            value=None,
            column=ColumnName.VEGNUMMER,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
        ),
        # Vegstatus
        DomainValue(
            value="V",
            column=ColumnName.VEGSTATUS,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
        ),
        DomainValue(
            value="U",
            column=ColumnName.VEGSTATUS,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
        ),
    ]
)


###############################
# Smart, fast lookup
###############################


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


###############################
# Extra for documentation
###############################


from datetime import date


def print_allowed_values(path: str = "Kolonneoversikt_AG.txt") -> None:
    sorted_items = sorted(
        DOMAIN_INDEX.items(),
        key=lambda item: (
            int(str(item[0][1].name).split("N")[-1]),  # scale
            item[0][2].name,  # object
            str(item[0][0]),  # column
        ),
    )

    lines: list[str] = [f"Rapport generert: {date.today()}"]

    n = 80
    current_scale = None
    current_object = None

    for (column, scale, obj), values in sorted_items:
        if scale != current_scale:
            current_scale = scale
            current_object = None
            lines.append(f"\n{'=' * n}")
            lines.append(f"SCALE: {scale.name}")
            lines.append(f"{'=' * n}")

        if obj != current_object:
            current_object = obj
            lines.append(f"{'-' * n}")
            lines.append(f"\nOBJECT: {obj.name}")
            lines.append(f"{'-' * n}")

        str_values = set([str(v) if v is not None else "None" for v in values])
        lines.append(
            f"\n{column}: {', '.join(v for v in sorted(str_values, key=lambda sv: sv.lower()))}"
        )

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"Rapport skrevet til '{path}'")


print_allowed_values()
