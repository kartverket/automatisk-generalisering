"""TEMPLATE / EXAMPLE — a worked pipeline. Target: `src/ag/tuning/scale/__init__.py`.

Cartographic constants shared ACROSS objects at one scale.

In reality this is `tuning/scale/`. One module per scale, holding the values that
are properties of the MAP rather than of any one pipeline: what is visible at this
scale, what separation reads as two features rather than one.

WHY THIS LAYER EXISTS SEPARATELY FROM AN OBJECT'S TUNING

"The minimum length a feature is visible at N100" is one cartographic fact. Road
thinning, river pruning and building elimination all spend it. Written three times it
drifts, and the drift is invisible: three pipelines each look internally consistent
and the map is not.

NAME THEM AFTER THE CARTOGRAPHIC CONCEPT, NOT THE CONSUMING PARAMETER.
`MINIMUM_VISIBLE_LENGTH_M`, never `THIN_MIN_LENGTH`. That is what makes
find-references answer a question a cartographer actually asks - "what else depends
on the visibility threshold" - rather than a question only this codebase asks.
"""
