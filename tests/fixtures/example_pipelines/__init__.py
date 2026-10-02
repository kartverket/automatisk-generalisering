"""The template's worked examples: two pipelines, their operations, tuning and identities.

Inert while the `ag.core` and `ag.ports` modules they import do not exist in `src/ag`:
excluded from type checking, linting and collection until then, and run meanwhile by the
template they came from. They are fixtures, not shipped code: their known defects are tracked
against them here, and they import each other as `example_pipelines.*`, never as `ag.*`, so
nothing under `ag` can depend on them.
"""
