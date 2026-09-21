Fokuserer på vei N100

Input data her er:

- Rådata
    - elveg_and_sti
    - vegsperring
- N50
    - ArealdekkeFlate
- N100
    - AdminFlate
    - AdminGrense
    - Anleggslinje
    - ArealdekkeFlate
    - Bane
    - Begrensningskurve

---

En pipeline baserer seg på:
- objekttype
- skala

(objekttype, skala) -> feature class -> felt

Når du starter en pipeline er det for en objekttype i en bestemt skala. Da er første spørsmål: "Hva trenger jeg av data for å kjøre denne pipelinen?"

Du må da kunne få ut en liste av feature classes fra dette oppslaget:

scale: {
    object: [...]
}

Hver av disse sendes videre til dataSet for å valideres og hente attributter. En ny lookup henter da alle felt uavhengig av hva feltet brukes til. Disse er på format:

felt = [navn, type, a, b, c ...]

... der enkeltbokstavene er heltall der:
- a: 1 = må eksistere i input, 0 ellers
- b: 1 = skal eksistere i endelig output, 0 ellers
- c: 1 = felt som må beholdes til senere generalisering, 0 ellers

Dette må være egne sett i DataSet.