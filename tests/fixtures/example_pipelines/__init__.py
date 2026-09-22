"""The template's worked examples: two pipelines, their operations, tuning and identities.

Inert until slice 1c: excluded from type checking, linting and collection, because the
`ag.core` and `ag.ports` modules they import do not exist in `src/ag` yet. Until then
`docs/refactor/template_code/tools/run_example.py` runs them against the template. They
are fixtures, not shipped code: the A17 defects are tracked against them here, and they
import each other as `example_pipelines.*`, never as `ag.*`, so nothing under `ag` can
depend on them (`project_tree.md` section 4).
"""
