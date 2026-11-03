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

    AREALDEKKE = auto()
    ELVEG_AND_STI = auto()
    VEGSPERRING = auto()


class ValueUsage(Flag):
    """Flags if the value is valid in a specific usage context."""

    RAW_DATA = auto()
    DURING_PROCESSING = auto()
    FINAL_OUTPUT = auto()
    FINAL_OUTPUT_PROCESSING = auto()


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
    usage: ValueUsage

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
            usage=(ValueUsage.RAW_DATA),
        ),
        # Adskiltelop
        DomainValue(
            value="med",
            column=ColumnName.ADSKILTELOP,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="mot",
            column=ColumnName.ADSKILTELOP,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value=None,
            column=ColumnName.ADSKILTELOP,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
            usage=(ValueUsage.RAW_DATA),
        ),
        # Adskiltelopnummer
        DomainValue(
            value=TypeValue(types=(str, type(None)), max_length=3),
            column=ColumnName.ADSKILTELOPNUMMER,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
            usage=(ValueUsage.RAW_DATA),
        ),
        # areal_m2
        DomainValue(
            value=RangeValue(min_value=0, max_value=np.inf),
            column=ColumnName.AREAL_M2,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        # arealbruk_hovedklasse
        DomainValue(
            value="Beredskap",
            column=ColumnName.AREALBRUK_HOVEDKLASSE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Boligbebyggelse",
            column=ColumnName.AREALBRUK_HOVEDKLASSE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Fritidsbebyggelse",
            column=ColumnName.AREALBRUK_HOVEDKLASSE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="GroenneOmr",
            column=ColumnName.AREALBRUK_HOVEDKLASSE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="HelseSosial",
            column=ColumnName.AREALBRUK_HOVEDKLASSE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="IdrettsOmr",
            column=ColumnName.AREALBRUK_HOVEDKLASSE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="KulturReligion",
            column=ColumnName.AREALBRUK_HOVEDKLASSE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="LandbrukFiske",
            column=ColumnName.AREALBRUK_HOVEDKLASSE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="NaeringTjeneste",
            column=ColumnName.AREALBRUK_HOVEDKLASSE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="TeknInfrastr",
            column=ColumnName.AREALBRUK_HOVEDKLASSE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="TransportTelek",
            column=ColumnName.AREALBRUK_HOVEDKLASSE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="UklassifisertBeb",
            column=ColumnName.AREALBRUK_HOVEDKLASSE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="UndervisnBhage",
            column=ColumnName.AREALBRUK_HOVEDKLASSE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value=None,
            column=ColumnName.AREALBRUK_HOVEDKLASSE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        # arealbruk_underklasse
        DomainValue(
            value="Alpinanlegg",
            column=ColumnName.AREALBRUK_UNDERKLASSE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="AnnenBilveg",
            column=ColumnName.AREALBRUK_UNDERKLASSE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="AnnenBolig",
            column=ColumnName.AREALBRUK_UNDERKLASSE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="AnnenVeg",
            column=ColumnName.AREALBRUK_UNDERKLASSE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="AnnetUndervisn",
            column=ColumnName.AREALBRUK_UNDERKLASSE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Bane",
            column=ColumnName.AREALBRUK_UNDERKLASSE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Barnehage",
            column=ColumnName.AREALBRUK_UNDERKLASSE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="BarneUngdSkole",
            column=ColumnName.AREALBRUK_UNDERKLASSE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Beredskap",
            column=ColumnName.AREALBRUK_UNDERKLASSE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Bergverk",
            column=ColumnName.AREALBRUK_UNDERKLASSE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="BoligNaering",
            column=ColumnName.AREALBRUK_UNDERKLASSE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Energiforsyning",
            column=ColumnName.AREALBRUK_UNDERKLASSE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="FiskeBeb",
            column=ColumnName.AREALBRUK_UNDERKLASSE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Fornoyelsespark",
            column=ColumnName.AREALBRUK_UNDERKLASSE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="FritidsBeb",
            column=ColumnName.AREALBRUK_UNDERKLASSE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="FrittliggSmaahus",
            column=ColumnName.AREALBRUK_UNDERKLASSE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="GangSykkelVeg",
            column=ColumnName.AREALBRUK_UNDERKLASSE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Golfanlegg",
            column=ColumnName.AREALBRUK_UNDERKLASSE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="GravUrnelund",
            column=ColumnName.AREALBRUK_UNDERKLASSE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="HovedVeg",
            column=ColumnName.AREALBRUK_UNDERKLASSE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="IdrettsBygning",
            column=ColumnName.AREALBRUK_UNDERKLASSE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Industri",
            column=ColumnName.AREALBRUK_UNDERKLASSE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="KaiHavnOmr",
            column=ColumnName.AREALBRUK_UNDERKLASSE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="KinoTeaterMm",
            column=ColumnName.AREALBRUK_UNDERKLASSE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="KonsSmaahus",
            column=ColumnName.AREALBRUK_UNDERKLASSE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="KontorForretning",
            column=ColumnName.AREALBRUK_UNDERKLASSE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="LegeHelse",
            column=ColumnName.AREALBRUK_UNDERKLASSE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Lekeplass",
            column=ColumnName.AREALBRUK_UNDERKLASSE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="LufthavnOmr",
            column=ColumnName.AREALBRUK_UNDERKLASSE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="MotorTrafikkVeg",
            column=ColumnName.AREALBRUK_UNDERKLASSE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Motorveg",
            column=ColumnName.AREALBRUK_UNDERKLASSE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="MuseerBibliotek",
            column=ColumnName.AREALBRUK_UNDERKLASSE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="OvernattingMm",
            column=ColumnName.AREALBRUK_UNDERKLASSE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Park",
            column=ColumnName.AREALBRUK_UNDERKLASSE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Parkering",
            column=ColumnName.AREALBRUK_UNDERKLASSE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Religion",
            column=ColumnName.AREALBRUK_UNDERKLASSE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Skytebane",
            column=ColumnName.AREALBRUK_UNDERKLASSE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="SportIdrPlass",
            column=ColumnName.AREALBRUK_UNDERKLASSE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="StoreBoligbygg",
            column=ColumnName.AREALBRUK_UNDERKLASSE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="SykehjemMm",
            column=ColumnName.AREALBRUK_UNDERKLASSE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Sykehus",
            column=ColumnName.AREALBRUK_UNDERKLASSE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="TerminalEksped",
            column=ColumnName.AREALBRUK_UNDERKLASSE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="TunOmr",
            column=ColumnName.AREALBRUK_UNDERKLASSE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="UklassifisertBeb",
            column=ColumnName.AREALBRUK_UNDERKLASSE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="UniversitetMm",
            column=ColumnName.AREALBRUK_UNDERKLASSE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="UtmarksBeb",
            column=ColumnName.AREALBRUK_UNDERKLASSE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="VannAvlRenov",
            column=ColumnName.AREALBRUK_UNDERKLASSE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="VegTrafikkTilsyn",
            column=ColumnName.AREALBRUK_UNDERKLASSE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="VideregSkole",
            column=ColumnName.AREALBRUK_UNDERKLASSE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value=None,
            column=ColumnName.AREALBRUK_UNDERKLASSE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        # arealdekke
        DomainValue(
            value="Bebygd",
            column=ColumnName.AREALDEKKE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Ferskvann_elv_bekk",
            column=ColumnName.AREALDEKKE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Ferskvann_innsjo_tjern",
            column=ColumnName.AREALDEKKE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Ferskvann_innsjo_tjern_regulert",
            column=ColumnName.AREALDEKKE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Ferskvann_kanal",
            column=ColumnName.AREALDEKKE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Hav",
            column=ColumnName.AREALDEKKE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Jordbruk_fulldyrka",
            column=ColumnName.AREALDEKKE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Jordbruk_innmarksbeite_aapen",
            column=ColumnName.AREALDEKKE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Jordbruk_innmarksbeite_tresatt",
            column=ColumnName.AREALDEKKE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Jordbruk_innmarksbeite_uspes",
            column=ColumnName.AREALDEKKE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Jordbruk_overflatedyrka",
            column=ColumnName.AREALDEKKE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Myr_aapen",
            column=ColumnName.AREALDEKKE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Myr_tresatt",
            column=ColumnName.AREALDEKKE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Samferdsel",
            column=ColumnName.AREALDEKKE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Skog",
            column=ColumnName.AREALDEKKE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Snaumark_frisk",
            column=ColumnName.AREALDEKKE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Snaumark_impediment",
            column=ColumnName.AREALDEKKE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Snaumark_konstruert",
            column=ColumnName.AREALDEKKE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Snaumark_middels_frisk",
            column=ColumnName.AREALDEKKE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Snaumark_skrinn",
            column=ColumnName.AREALDEKKE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Snaumark_uspesifisert",
            column=ColumnName.AREALDEKKE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Snoisbre",
            column=ColumnName.AREALDEKKE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        # bruktflagg
        DomainValue(
            value=RangeValue(min_value=0, max_value=11),
            column=ColumnName.BRUKTFLAGG,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        # dgfcd_feature_531
        DomainValue(
            value="AK120",
            column=ColumnName.DGFCD_FEATURE_531,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="AL020",
            column=ColumnName.DGFCD_FEATURE_531,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="AL030",
            column=ColumnName.DGFCD_FEATURE_531,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="BH140",
            column=ColumnName.DGFCD_FEATURE_531,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="EA010",
            column=ColumnName.DGFCD_FEATURE_531,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="EB060",
            column=ColumnName.DGFCD_FEATURE_531,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="EE020",
            column=ColumnName.DGFCD_FEATURE_531,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value=None,
            column=ColumnName.DGFCD_FEATURE_531,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        # dgfcd_feature_alpha
        DomainValue(
            value="BuiltUpArea",
            column=ColumnName.DGFCD_FEATURE_ALPHA,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Cemetery",
            column=ColumnName.DGFCD_FEATURE_ALPHA,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="CropLand",
            column=ColumnName.DGFCD_FEATURE_ALPHA,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Heathland",
            column=ColumnName.DGFCD_FEATURE_ALPHA,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="InlandWaterbody",
            column=ColumnName.DGFCD_FEATURE_ALPHA,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Park",
            column=ColumnName.DGFCD_FEATURE_ALPHA,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="River",
            column=ColumnName.DGFCD_FEATURE_ALPHA,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="UnvegetatedLand",
            column=ColumnName.DGFCD_FEATURE_ALPHA,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value=None,
            column=ColumnName.DGFCD_FEATURE_ALPHA,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        # dgif_ccode
        DomainValue(
            value="AK120_0_0",
            column=ColumnName.DGIF_CCODE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="AL020_0_0",
            column=ColumnName.DGIF_CCODE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="AL020_FUC_13",
            column=ColumnName.DGIF_CCODE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="AL020_FUC_19",
            column=ColumnName.DGIF_CCODE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="AL030_0_0",
            column=ColumnName.DGIF_CCODE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="BH140_0_0",
            column=ColumnName.DGIF_CCODE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="EA010_0_0",
            column=ColumnName.DGIF_CCODE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="EB060_0_0",
            column=ColumnName.DGIF_CCODE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="EE020_0_0",
            column=ColumnName.DGIF_CCODE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="EE020_TSM_3",
            column=ColumnName.DGIF_CCODE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value=None,
            column=ColumnName.DGIF_CCODE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        # Eier
        DomainValue(
            value="fylkeskommune",
            column=ColumnName.EIER,
            scales=(DomainScale.N100),
            objects=(DomainObject.VEGSPERRING),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="kommune",
            column=ColumnName.EIER,
            scales=(DomainScale.N100),
            objects=(DomainObject.VEGSPERRING),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="NyeVeier",
            column=ColumnName.EIER,
            scales=(DomainScale.N100),
            objects=(DomainObject.VEGSPERRING),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="privat",
            column=ColumnName.EIER,
            scales=(DomainScale.N100),
            objects=(DomainObject.VEGSPERRING),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="StatensVegvesen",
            column=ColumnName.EIER,
            scales=(DomainScale.N100),
            objects=(DomainObject.VEGSPERRING),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="uavklart",
            column=ColumnName.EIER,
            scales=(DomainScale.N100),
            objects=(DomainObject.VEGSPERRING),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value=None,
            column=ColumnName.EIER,
            scales=(DomainScale.N100),
            objects=(DomainObject.VEGSPERRING),
            usage=(ValueUsage.RAW_DATA),
        ),
        # Feltoversikt
        DomainValue(
            value=TypeValue(types=(str, type(None)), max_length=50),
            column=ColumnName.FELTOVERSIKT,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
            usage=(ValueUsage.RAW_DATA),
        ),
        # Funksjon
        DomainValue(
            value="betalingssperring",
            column=ColumnName.FUNKSJON,
            scales=(DomainScale.N100),
            objects=(DomainObject.VEGSPERRING),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="bussluse",
            column=ColumnName.FUNKSJON,
            scales=(DomainScale.N100),
            objects=(DomainObject.VEGSPERRING),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="fjernstyrtSperring",
            column=ColumnName.FUNKSJON,
            scales=(DomainScale.N100),
            objects=(DomainObject.VEGSPERRING),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="låstSperring",
            column=ColumnName.FUNKSJON,
            scales=(DomainScale.N100),
            objects=(DomainObject.VEGSPERRING),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="trafikkavviser",
            column=ColumnName.FUNKSJON,
            scales=(DomainScale.N100),
            objects=(DomainObject.VEGSPERRING),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="ulåstSperring",
            column=ColumnName.FUNKSJON,
            scales=(DomainScale.N100),
            objects=(DomainObject.VEGSPERRING),
            usage=(ValueUsage.RAW_DATA),
        ),
        # grunnforhold
        DomainValue(
            value="Blokkmark",
            column=ColumnName.GRUNNFORHOLD,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Fjell_i_dagen",
            column=ColumnName.GRUNNFORHOLD,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Grunnlendt",
            column=ColumnName.GRUNNFORHOLD,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Ikke_kartlagt",
            column=ColumnName.GRUNNFORHOLD,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Ikke_relevant",
            column=ColumnName.GRUNNFORHOLD,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Jorddekt",
            column=ColumnName.GRUNNFORHOLD,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Konstruert",
            column=ColumnName.GRUNNFORHOLD,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Organisk_jordlag",
            column=ColumnName.GRUNNFORHOLD,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        # grunnkart_kilde
        DomainValue(
            value="Ar5",
            column=ColumnName.GRUNNKART_KILDE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Ar50",
            column=ColumnName.GRUNNKART_KILDE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Arstat_2017",
            column=ColumnName.GRUNNKART_KILDE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="FKBvann",
            column=ColumnName.GRUNNKART_KILDE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="N50",
            column=ColumnName.GRUNNKART_KILDE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Ssbarealbruk",
            column=ColumnName.GRUNNKART_KILDE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Ssbhav",
            column=ColumnName.GRUNNKART_KILDE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        # havarealbrukstedbundet
        DomainValue(
            value="Akvakultur- akvakulturdyr",
            column=ColumnName.HAVAREALBRUKSTEDSBUNDET,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Akvakultur- Alger",
            column=ColumnName.HAVAREALBRUKSTEDSBUNDET,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Akvakultur- andre arter",
            column=ColumnName.HAVAREALBRUKSTEDSBUNDET,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Akvakultur- Havbeite",
            column=ColumnName.HAVAREALBRUKSTEDSBUNDET,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Akvakultur- Matfisk",
            column=ColumnName.HAVAREALBRUKSTEDSBUNDET,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Akvakultur- Sartillatelser",
            column=ColumnName.HAVAREALBRUKSTEDSBUNDET,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Akvakultur- Slaktemerd",
            column=ColumnName.HAVAREALBRUKSTEDSBUNDET,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Akvakultur- Stamfisk",
            column=ColumnName.HAVAREALBRUKSTEDSBUNDET,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Avlop",
            column=ColumnName.HAVAREALBRUKSTEDSBUNDET,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Dumpefelt",
            column=ColumnName.HAVAREALBRUKSTEDSBUNDET,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Flytebrygge",
            column=ColumnName.HAVAREALBRUKSTEDSBUNDET,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Flytedokk",
            column=ColumnName.HAVAREALBRUKSTEDSBUNDET,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Kai- og Havneomraader",
            column=ColumnName.HAVAREALBRUKSTEDSBUNDET,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Mudret Omraade",
            column=ColumnName.HAVAREALBRUKSTEDSBUNDET,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Vrak",
            column=ColumnName.HAVAREALBRUKSTEDSBUNDET,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value=None,
            column=ColumnName.HAVAREALBRUKSTEDSBUNDET,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        # havfiskeribruk
        DomainValue(
            value="Fiskeplasser- ERS",
            column=ColumnName.HAVFISKERIBRUK,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Kystnare fiskeplasser",
            column=ColumnName.HAVFISKERIBRUK,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Laassettingsplasser",
            column=ColumnName.HAVFISKERIBRUK,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value=None,
            column=ColumnName.HAVFISKERIBRUK,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        # hoyde
        DomainValue(
            value=TypeValue(types=(str, type(None)), max_length=50),
            column=ColumnName.HOYDE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        # id
        DomainValue(
            value=RangeValue(min_value=1, max_value=np.inf),
            column=ColumnName.ID,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        # komid
        DomainValue(
            value=RangeValue(min_value=100, max_value=10_000),
            column=ColumnName.KOMID,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        # Konnekteringslenke
        DomainValue(
            value="NEI",
            column=ColumnName.KONNEKTERINGSLENKE,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="JA",
            column=ColumnName.KONNEKTERINGSLENKE,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value=None,
            column=ColumnName.KONNEKTERINGSLENKE,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
            usage=(ValueUsage.RAW_DATA),
        ),
        # Kryssdel
        DomainValue(
            value=None,
            column=ColumnName.KRYSSDEL,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value=RangeValue(min_value=1, max_value=14),
            column=ColumnName.KRYSSDEL,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
            usage=(ValueUsage.RAW_DATA),
        ),
        # LRV
        DomainValue(
            value=RangeValue(min_value=-np.inf, max_value=np.inf),
            column=ColumnName.LRV,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value=None,
            column=ColumnName.LRV,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        # Medium
        DomainValue(
            value="B",
            column=ColumnName.MEDIUM,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="L",
            column=ColumnName.MEDIUM,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="T",
            column=ColumnName.MEDIUM,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="U",
            column=ColumnName.MEDIUM,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
            usage=(ValueUsage.RAW_DATA),
        ),
        # Motorvegtype
        DomainValue(
            value="Ikke motorveg",
            column=ColumnName.MOTORVEGTYPE,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Motortrafikkveg",
            column=ColumnName.MOTORVEGTYPE,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Motorveg",
            column=ColumnName.MOTORVEGTYPE,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Udefinert",
            column=ColumnName.MOTORVEGTYPE,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
            usage=(ValueUsage.RAW_DATA),
        ),
        # Objtype
        DomainValue(
            value="Barmarksløype",
            column=ColumnName.OBJTYPE,
            scales=(DomainScale.N50 | DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="GangSykkelveg",
            column=ColumnName.OBJTYPE,
            scales=(DomainScale.N50 | DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
            usage=(ValueUsage.RAW_DATA),
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
            usage=(ValueUsage.RAW_DATA),
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
            usage=(ValueUsage.RAW_DATA),
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
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Vegsperring",
            column=ColumnName.OBJTYPE,
            scales=(DomainScale.N100),
            objects=(DomainObject.VEGSPERRING),
            usage=(ValueUsage.RAW_DATA),
        ),
        # okosystemtype_1
        DomainValue(
            value="Coastal beaches, dunes and wetlands",
            column=ColumnName.OKOSYSTEMTYPE_1,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Cropland",
            column=ColumnName.OKOSYSTEMTYPE_1,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Forest and woodlands",
            column=ColumnName.OKOSYSTEMTYPE_1,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Grassland",
            column=ColumnName.OKOSYSTEMTYPE_1,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Heathland and shrub",
            column=ColumnName.OKOSYSTEMTYPE_1,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Inland wetlands",
            column=ColumnName.OKOSYSTEMTYPE_1,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Lakes and reservoirs",
            column=ColumnName.OKOSYSTEMTYPE_1,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Marine ecosystems",
            column=ColumnName.OKOSYSTEMTYPE_1,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Rivers and canals",
            column=ColumnName.OKOSYSTEMTYPE_1,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Settlements and other artificial areas",
            column=ColumnName.OKOSYSTEMTYPE_1,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Sparsely vegetated ecosystems",
            column=ColumnName.OKOSYSTEMTYPE_1,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        # okosystemtype_2
        DomainValue(
            value="Artificial reservoirs",
            column=ColumnName.OKOSYSTEMTYPE_2,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Broadleaved deciduous forest",
            column=ColumnName.OKOSYSTEMTYPE_2,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Canals, ditches and drains",
            column=ColumnName.OKOSYSTEMTYPE_2,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Coniferous forests",
            column=ColumnName.OKOSYSTEMTYPE_2,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Continuous settlement area",
            column=ColumnName.OKOSYSTEMTYPE_2,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Discontinuous settlement area",
            column=ColumnName.OKOSYSTEMTYPE_2,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Ice sheets, glaciers and perennial snowfields",
            column=ColumnName.OKOSYSTEMTYPE_2,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Infrastructure",
            column=ColumnName.OKOSYSTEMTYPE_2,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Lakes and ponds",
            column=ColumnName.OKOSYSTEMTYPE_2,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Mires, bogs and fens",
            column=ColumnName.OKOSYSTEMTYPE_2,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Mixed forests",
            column=ColumnName.OKOSYSTEMTYPE_2,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Other artificial areas",
            column=ColumnName.OKOSYSTEMTYPE_2,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Rivers",
            column=ColumnName.OKOSYSTEMTYPE_2,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Scrub and heathland",
            column=ColumnName.OKOSYSTEMTYPE_2,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Urban greenspace",
            column=ColumnName.OKOSYSTEMTYPE_2,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value=None,
            column=ColumnName.OKOSYSTEMTYPE_2,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        # okosystemtype_3
        DomainValue(
            value="Airports",
            column=ColumnName.OKOSYSTEMTYPE_3,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Cemeteries",
            column=ColumnName.OKOSYSTEMTYPE_3,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Continuous commercial and industrial area",
            column=ColumnName.OKOSYSTEMTYPE_3,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Continuous residential area",
            column=ColumnName.OKOSYSTEMTYPE_3,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Discontinuous commercial and industrial area",
            column=ColumnName.OKOSYSTEMTYPE_3,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Discontinuous residential area",
            column=ColumnName.OKOSYSTEMTYPE_3,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Mineral extraction sites",
            column=ColumnName.OKOSYSTEMTYPE_3,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Other infrastructure",
            column=ColumnName.OKOSYSTEMTYPE_3,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Parks",
            column=ColumnName.OKOSYSTEMTYPE_3,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Port areas",
            column=ColumnName.OKOSYSTEMTYPE_3,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Road and rail networks and associated land",
            column=ColumnName.OKOSYSTEMTYPE_3,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Sports and recreation sites",
            column=ColumnName.OKOSYSTEMTYPE_3,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value=None,
            column=ColumnName.OKOSYSTEMTYPE_3,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        # okosystemtype_kode
        DomainValue(
            value=TypeValue(types=(str,), max_length=10),
            column=ColumnName.OKOSYSTEMTYPE_KODE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        # omkrets
        DomainValue(
            value=RangeValue(min_value=0, max_value=np.inf),
            column=ColumnName.OMKRETS,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        # partition_selection_field
        DomainValue(
            value=RangeValue(min_value=1, max_value=1),
            column=ColumnName.PARTITION_SELECTION_FIELD,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value=None,
            column=ColumnName.PARTITION_SELECTION_FIELD,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        # Rutemerking
        DomainValue(
            value="NEI",
            column=ColumnName.RUTEMERKING,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="JA",
            column=ColumnName.RUTEMERKING,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Udefinert",
            column=ColumnName.RUTEMERKING,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value=None,
            column=ColumnName.RUTEMERKING,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
            usage=(ValueUsage.RAW_DATA),
        ),
        # Sideanleggsdel
        DomainValue(
            value=RangeValue(min_value=1, max_value=6),
            column=ColumnName.SIDEANLEGGSDEL,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value=None,
            column=ColumnName.SIDEANLEGGSDEL,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
            usage=(ValueUsage.RAW_DATA),
        ),
        # skogbonitet
        DomainValue(
            value="Hoy_bonitet",
            column=ColumnName.SKOGBONITET,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Ikke_kartlagt",
            column=ColumnName.SKOGBONITET,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Ikke_relevant",
            column=ColumnName.SKOGBONITET,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Impediment",
            column=ColumnName.SKOGBONITET,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Lav_bonitet",
            column=ColumnName.SKOGBONITET,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Middels_bonitet",
            column=ColumnName.SKOGBONITET,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Saers_hoy_bonitet",
            column=ColumnName.SKOGBONITET,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        # ssbarealbruk_kilde
        DomainValue(
            value="AkvaFlate SSB",
            column=ColumnName.SSBAREALBRUK_KILDE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Ar5",
            column=ColumnName.SSBAREALBRUK_KILDE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="ArealMedBygg",
            column=ColumnName.SSBAREALBRUK_KILDE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Arstat",
            column=ColumnName.SSBAREALBRUK_KILDE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="DrivhusSsb",
            column=ColumnName.SSBAREALBRUK_KILDE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="ERS, fiskeiromraader SSB",
            column=ColumnName.SSBAREALBRUK_KILDE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="fiskeiromraader SSB",
            column=ColumnName.SSBAREALBRUK_KILDE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="FKB-BygnAnlegg",
            column=ColumnName.SSBAREALBRUK_KILDE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="FKB-BygnAnlegg ,Kystnare fiskeridata",
            column=ColumnName.SSBAREALBRUK_KILDE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="FKBAnlegg",
            column=ColumnName.SSBAREALBRUK_KILDE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="FkbAnleggSsb",
            column=ColumnName.SSBAREALBRUK_KILDE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="FkbArealbruk",
            column=ColumnName.SSBAREALBRUK_KILDE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="FkbArealbrukSsb",
            column=ColumnName.SSBAREALBRUK_KILDE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="FkbJernbaneSsb",
            column=ColumnName.SSBAREALBRUK_KILDE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="FkbLedningSsb",
            column=ColumnName.SSBAREALBRUK_KILDE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="FkbVeg",
            column=ColumnName.SSBAREALBRUK_KILDE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="FraPlan",
            column=ColumnName.SSBAREALBRUK_KILDE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="HavnPunktdataSsb",
            column=ColumnName.SSBAREALBRUK_KILDE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="KaiHavner Ssb",
            column=ColumnName.SSBAREALBRUK_KILDE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="KaiHavner Ssb ,Kystnare fiskeridata",
            column=ColumnName.SSBAREALBRUK_KILDE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="KrissSsb",
            column=ColumnName.SSBAREALBRUK_KILDE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Kystnare fiskeridata",
            column=ColumnName.SSBAREALBRUK_KILDE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="N50Arealdekke",
            column=ColumnName.SSBAREALBRUK_KILDE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="N50ArealdekkeSsb",
            column=ColumnName.SSBAREALBRUK_KILDE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="NguKunstig",
            column=ColumnName.SSBAREALBRUK_KILDE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="NvdbSsb",
            column=ColumnName.SSBAREALBRUK_KILDE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="NvePunktdataSsb",
            column=ColumnName.SSBAREALBRUK_KILDE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="PplRegister",
            column=ColumnName.SSBAREALBRUK_KILDE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Sjokart - Dybdedata",
            column=ColumnName.SSBAREALBRUK_KILDE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Sjokart - Dybdedata ,Kystnare fiskeridata",
            column=ColumnName.SSBAREALBRUK_KILDE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Sjokart - Maritim infrastruktur",
            column=ColumnName.SSBAREALBRUK_KILDE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Sjokart - Maritim infrastruktur",
            column=ColumnName.SSBAREALBRUK_KILDE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Sjokart - Maritim infrastruktur ,Kystnare fiskeridata",
            column=ColumnName.SSBAREALBRUK_KILDE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="SSB Hav",
            column=ColumnName.SSBAREALBRUK_KILDE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Utslippspunkt, buffer SSB",
            column=ColumnName.SSBAREALBRUK_KILDE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Utslippspunkt, buffer SSB ,Kystnare fiskeridata",
            column=ColumnName.SSBAREALBRUK_KILDE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Vegkant",
            column=ColumnName.SSBAREALBRUK_KILDE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value=None,
            column=ColumnName.SSBAREALBRUK_KILDE,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        # Subtypekode
        DomainValue(
            value=TypeValue(types=(str,), max_length=200),
            column=ColumnName.SUBTYPEKODE,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
            usage=(ValueUsage.RAW_DATA),
        ),
        # Treslag
        DomainValue(
            value="Barblanding",
            column=ColumnName.TRESLAG,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Blanding",
            column=ColumnName.TRESLAG,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Furu",
            column=ColumnName.TRESLAG,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Gran",
            column=ColumnName.TRESLAG,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Ikke_relevant",
            column=ColumnName.TRESLAG,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Lauv",
            column=ColumnName.TRESLAG,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Uspesifisert",
            column=ColumnName.TRESLAG,
            scales=(DomainScale.N10),
            objects=(DomainObject.AREALDEKKE),
            usage=(ValueUsage.RAW_DATA),
        ),
        # Type
        DomainValue(
            value="betongkjegle",
            column=ColumnName.TYPE,
            scales=(DomainScale.N100),
            objects=(DomainObject.VEGSPERRING),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="bilsperre",
            column=ColumnName.TYPE,
            scales=(DomainScale.N100),
            objects=(DomainObject.VEGSPERRING),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="bomMedAutomatiskÅpner",
            column=ColumnName.TYPE,
            scales=(DomainScale.N100),
            objects=(DomainObject.VEGSPERRING),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="bussluse",
            column=ColumnName.TYPE,
            scales=(DomainScale.N100),
            objects=(DomainObject.VEGSPERRING),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="låstBom",
            column=ColumnName.TYPE,
            scales=(DomainScale.N100),
            objects=(DomainObject.VEGSPERRING),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="newJersey",
            column=ColumnName.TYPE,
            scales=(DomainScale.N100),
            objects=(DomainObject.VEGSPERRING),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="rørgelender",
            column=ColumnName.TYPE,
            scales=(DomainScale.N100),
            objects=(DomainObject.VEGSPERRING),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="steinblokk",
            column=ColumnName.TYPE,
            scales=(DomainScale.N100),
            objects=(DomainObject.VEGSPERRING),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="trafikkavviser",
            column=ColumnName.TYPE,
            scales=(DomainScale.N100),
            objects=(DomainObject.VEGSPERRING),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value=None,
            column=ColumnName.TYPE,
            scales=(DomainScale.N100),
            objects=(DomainObject.VEGSPERRING),
            usage=(ValueUsage.RAW_DATA),
        ),
        # Typeveg
        DomainValue(
            value="Barmarksløype",
            column=ColumnName.TYPEVEG,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="bilferje",
            column=ColumnName.TYPEVEG,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="enkelBilveg",
            column=ColumnName.TYPEVEG,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Gang- og Sykkelveg",
            column=ColumnName.TYPEVEG,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="kanalisertVeg",
            column=ColumnName.TYPEVEG,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="passasjerferje",
            column=ColumnName.TYPEVEG,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Privat Veg",
            column=ColumnName.TYPEVEG,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="rampe",
            column=ColumnName.TYPEVEG,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="rundkjøring",
            column=ColumnName.TYPEVEG,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Sti DNT",
            column=ColumnName.TYPEVEG,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Sti ikke merket",
            column=ColumnName.TYPEVEG,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Sti merket",
            column=ColumnName.TYPEVEG,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Traktorveg",
            column=ColumnName.TYPEVEG,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
            usage=(ValueUsage.RAW_DATA),
        ),
        # Uttegning
        DomainValue(
            value="1 vinge",
            column=ColumnName.UTTEGNING,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value=None,
            column=ColumnName.UTTEGNING,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
            usage=(ValueUsage.RAW_DATA),
        ),
        # Vedlikeh
        DomainValue(
            value="Andre",
            column=ColumnName.VEDLIKEH,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="DNT",
            column=ColumnName.VEDLIKEH,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="Udefinert",
            column=ColumnName.VEDLIKEH,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value=None,
            column=ColumnName.VEDLIKEH,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
            usage=(ValueUsage.RAW_DATA),
        ),
        # Vegkategori
        DomainValue(
            value="E",
            column=ColumnName.VEGKATEGORI,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="F",
            column=ColumnName.VEGKATEGORI,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="K",
            column=ColumnName.VEGKATEGORI,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="P",
            column=ColumnName.VEGKATEGORI,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="R",
            column=ColumnName.VEGKATEGORI,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="S",
            column=ColumnName.VEGKATEGORI,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value=None,
            column=ColumnName.VEGKATEGORI,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
            usage=(ValueUsage.RAW_DATA),
        ),
        # Vegklasse
        DomainValue(
            value=RangeValue(min_value=1, max_value=9),
            column=ColumnName.VEGKLASSE,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value=None,
            column=ColumnName.VEGKLASSE,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
            usage=(ValueUsage.RAW_DATA),
        ),
        # Vegnummer
        DomainValue(
            value=TypeValue(types=(int, float)),
            column=ColumnName.VEGNUMMER,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value=None,
            column=ColumnName.VEGNUMMER,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
            usage=(ValueUsage.RAW_DATA),
        ),
        # Vegstatus
        DomainValue(
            value="V",
            column=ColumnName.VEGSTATUS,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
            usage=(ValueUsage.RAW_DATA),
        ),
        DomainValue(
            value="U",
            column=ColumnName.VEGSTATUS,
            scales=(DomainScale.N100),
            objects=(DomainObject.ELVEG_AND_STI),
            usage=(ValueUsage.RAW_DATA),
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
