import arcpy


'''
Hent data
- Trekker ut innsjøer og regulerte innsjøer fra arealdekket og gjør dem om til egen fc.

Data bearbeiding
- Fikse kommunegrenser som kutter innsjøer i biter: Dissolve -> multi-to-singlepart -> spatial join

Finne innsjoer under minstemål
- Velge ut innsjøer under minimumsmål ved å opprette en minimumsbøffer rundt innsjø kanten (polygon to line) og deretter erase. 
- Samme minstemål som elvene på minimum 6 meter bredde
- Buffre områdene igjen fra den negative minimumsbøfferen for at den skal få ca. opprinnelig størrelse. 
- Erase store innsjø segmenter fra opprinnelig elvelag og gjør dette om til ny fc.

Buffe innsjø segmenter under minstemål (denne burde deles opp!)
- Kjør en multi to single part på innsjø segmentene under minstekrav.
- Opprett en "overkill buffer" på ca. 10 Meter rundt innsjø segmentene.
- Clip innsjøene etter det som passer inni overkill bøfferne.
- Kjør en collapse hydro polygon for å finne midtlinje til bitene.
- Erase områdene over minimum fra midtlinjen.
- Buff midtlinjene med 3 meter for at de skal akkurat fylle minimumskravet.
- Opprett en ny fc som er en merge mellom de originale innsjøene og de nye forstørrede bitene.

Aggregering
- Aggreger små innsjøer som er veldig nærme hverandre. 7 meter aggregation distance virker greit hittil.
**

Forenkle innsjø kantene med smoothing og simplify algoritme

Hierarkiet

1. Laveste nivå: minstemål på øyene. Disse fjernes fullstendig
2. Middels nivå: hvis øyer har flere lag, f.eks. skog og snaumark, spiser det største arealet opp det/de andre arealet.
'''