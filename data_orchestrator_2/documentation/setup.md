# GIS-generalisering: data- og pipelinemodell

## Formål

Dette dokumentet beskriver en foreslått arkitektur for:

- validering av inputdata før en pipeline starter
- kontroll av skjema, felter og kolonner
- opprydding av felter under prosessering
- klargjøring av datasett for videre generalisering og distribusjon

Målet er å etablere én sentral kilde til sannhet for hvilke datasett og felter som finnes, og hvordan de brukes gjennom hele generaliseringsløpet.

## Designprinsipper

Modellen består av fire sentrale deler:

```text
FieldDefinition
        |
        v
DataSetDefinition
        |
        v
PipelineDefinition
        |
        +--> Validator
        +--> FieldManager
```

Ansvarsfordelingen er:

- **Pipeline** vet hvilke datasett som trengs.
- **Datasett** vet hvilke felter som forventes.
- **Felt** beskriver hvordan de brukes gjennom pipelinen.
- **Validator** kontrollerer at forutsetningene er oppfylt.
- **FieldManager** rydder opp i felter underveis og før eksport.

## Komposisjon fremfor arv

Modellen bør bruke komposisjon, altså har-en-relasjoner, og ikke arv. Et datasett er ikke et felt, og en pipeline er ikke et datasett.

```text
Pipeline
├── DataSet
│   ├── Field
│   ├── Field
│   └── Field
└── DataSet
    ├── Field
    └── Field
```

Dette bør unngås:

```python
class DataSet(Field):
    ...
```

## Feltmodell

### `FieldUsage`

Et felt kan ha flere roller i løpet av pipelinen. En `Flag`-enum uttrykker dette bedre enn flere boolske variabler.

```python
from enum import Flag, auto


class FieldUsage(Flag):
    INPUT = auto()
    PROCESSING = auto()
    OUTPUT = auto()
```

Et felt som skal leses inn, brukes under prosessering og leveres i sluttproduktet, kan bruke alle tre flaggene:

```python
FieldUsage.INPUT | FieldUsage.PROCESSING | FieldUsage.OUTPUT
```

### `FieldDefinition`

`FieldDefinition` beskriver feltnavn, logisk datatype og bruksområde.

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class FieldDefinition:
    name: str
    datatype: str
    usage: FieldUsage
```

Eksempler:

```python
OBJTYPE = FieldDefinition(
    name="objtype",
    datatype="TEXT",
    usage=(
        FieldUsage.INPUT
        | FieldUsage.PROCESSING
        | FieldUsage.OUTPUT
    ),
)

OBJID = FieldDefinition(
    name="objid",
    datatype="LONG",
    usage=FieldUsage.INPUT,
)

HIERARCHY = FieldDefinition(
    name="hierarchy",
    datatype="SHORT",
    usage=FieldUsage.INPUT | FieldUsage.PROCESSING,
)

VEGNUMMER = FieldDefinition(
    name="vegnummer",
    datatype="TEXT",
    usage=FieldUsage.INPUT | FieldUsage.OUTPUT,
)
```

## Sentralt feltregister

Alle felter bør samles i ett sentralt register. Da vedlikeholdes navn og datatyper på ett sted, og definisjonene kan gjenbrukes av datasett, validator og `FieldManager`.

```python
class Fields:
    OBJTYPE = OBJTYPE
    OBJID = OBJID
    HIERARCHY = HIERARCHY
    VEGNUMMER = VEGNUMMER
```

Bruk:

```python
Fields.OBJTYPE
```

Fordeler:

- ett sted å vedlikeholde felter
- ingen duplisering av feltnavn og datatyper
- samme definisjon brukes i hele systemet
- færre hardkodede kolonnenavn i prosesseringskoden

## Datasettmodell

### `DataSetDefinition`

Et datasett beskriver forventet innhold i en feature class, men ikke hvor den konkrete filen ligger.

```python
@dataclass(frozen=True)
class DataSetDefinition:
    name: str
    source: str
    fields: tuple[FieldDefinition, ...]
```

Eksempel:

```python
ELVEG_AND_STI = DataSetDefinition(
    name="elveg_and_sti",
    source="raw",
    fields=(
        Fields.OBJTYPE,
        Fields.OBJID,
        Fields.HIERARCHY,
    ),
)
```

### Definisjon versus faktisk datasett

`DataSetDefinition` beskriver hvilke felter som skal finnes, hvordan de brukes og hvilken logisk datatype de har. Et faktisk datasett beskriver dataene på disk, den aktuelle geodatabasen og filstien.

```python
@dataclass(frozen=True)
class FeatureClass:
    definition: DataSetDefinition
    path: str


elveg_and_sti = FeatureClass(
    definition=ELVEG_AND_STI,
    path="C:/data/n100.gdb/elveg_and_sti",
)
```

Den samme definisjonen kan dermed brukes i utvikling, test og produksjon uten duplisering.

## Pipelinemodell

### `PipelineDefinition`

En pipeline beskriver hvilke datasett som kreves for å produsere et gitt produkt.

```python
@dataclass(frozen=True)
class PipelineDefinition:
    object_type: str
    scale: str
    datasets: tuple[DataSetDefinition, ...]
```

Eksempel for N100 vei:

```python
N100_VEI = PipelineDefinition(
    object_type="vei",
    scale="n100",
    datasets=(
        ELVEG_AND_STI,
        VEGSPERRING,
        ADMIN_FLATE,
        ADMIN_GRENSE,
        ANLEGGSLINJE,
        BANE,
        BEGRENSNINGSKURVE,
        AREALDEKKE_FLATE,
    ),
)
```

Alle pipelines registreres sentralt:

```python
PIPELINES = {
    ("vei", "n100"): N100_VEI,
}

pipeline = PIPELINES[("vei", "n100")]
```

## Validering

Når en pipeline starter, bør validatoren kontrollere alle nødvendige forutsetninger og samle feil i én rapport.

### Kontroller

1. Finnes feature class?
2. Har datasettet innhold?
3. Finnes alle nødvendige inputfelter?

Bare felter som er merket med `FieldUsage.INPUT`, skal være obligatoriske ved innlesing.

Eksempel på en samlet rapport:

```text
Datasett:
  OK     elveg_and_sti
  OK     vegsperring
  FEIL   bane: feature class finnes ikke

Innhold:
  OK     elveg_and_sti: 12 034 objekter
  FEIL   vegsperring: datasettet er tomt

Inputfelter:
  OK     objtype
  OK     objid
  FEIL   medium: feltet mangler
```

Et mulig grensesnitt er:

```python
class Validator:
    def validate_pipeline(
        self,
        pipeline: PipelineDefinition,
    ) -> ValidationResult:
        ...
```

Validatoren bør returnere en `ValidationResult` og ikke stoppe ved første feil. Det gir én samlet rapport som er enklere å rette opp.

## `FieldManager`

`FieldManager` har ansvar for kolonnehåndtering gjennom hele prosessen:

- opprydding før neste generaliseringstrinn
- skjema- og feltkontroll
- opprydding før eksport

### Opprydding for videre prosessering

Underveis beholdes bare felter som er merket med `FieldUsage.PROCESSING`.

```python
field_manager.cleanup_for_processing(feature_class)
```

Midlertidige felter som `tmp_area`, `tmp_class` og `tmp_selection` kan opprettes av et trinn og fjernes når de ikke lenger trengs.

### Klargjøring av sluttprodukt

Før distribusjon beholdes bare felter som er merket med `FieldUsage.OUTPUT`.

```python
field_manager.prepare_final_output(feature_class)
```

```text
Før:
  objid
  tmp_length
  tmp_area
  hierarchy
  objtype
  vegnummer

Etter:
  objtype
  vegnummer
```

Dette fjerner hjelpedata, temporære felter, interne ID-er og generaliseringsfelter før sluttproduktet leveres.

## Typisk arbeidsflyt

```python
pipeline = PIPELINES[("vei", "n100")]

validation_result = validator.validate_pipeline(pipeline)
validation_result.raise_if_invalid()

for dataset in pipeline.datasets:
    feature_class = data_reader.read(dataset)
    run_generalization_steps(feature_class)
    field_manager.cleanup_for_processing(feature_class)

field_manager.prepare_final_output(feature_class)
```

Arbeidsflyten er:

1. Slå opp riktig pipeline.
2. Valider datasett, innhold og inputfelter.
3. Kjør generaliseringstrinnene.
4. Rydd bort felter som ikke skal brukes videre.
5. Klargjør sluttproduktet med kun distribusjonsfeltene.

## Resultat

Med denne modellen får systemet:

- én sentral definisjon av alle felter, datasett og pipelines
- automatisk validering før kjøring
- automatisk kolonneopprydding underveis
- automatisk klargjøring for distribusjon
- et klart skille mellom logisk definisjon og faktisk data på disk
- en modell som kan skaleres fra N100 vei til N50, N250 og andre objekttyper

Den viktigste gevinsten er at skjema, validering og opprydding styres av den samme metadata-modellen. Når et nytt felt legges til eller fjernes, endres definisjonen ett sted, og resten av systemet kan følge automatisk etter.

## Anbefalt videre arbeid

1. Avklar hvilke datatyper som skal støttes av `FieldDefinition`.
2. Implementer `ValidationResult` med samlede feil og advarsler.
3. Koble `FieldManager` til eksisterende ArcPy-funksjoner.
4. Definer datasett- og pipeline-registeret for produksjonsløpene.
5. Legg til tester for validering, feltopprydding og sluttprodukt.