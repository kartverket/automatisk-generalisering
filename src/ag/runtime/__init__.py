"""The composition root for a pod: settings, toolbox composition, stage resolution, the
stage entry loop, the local runner, fan-out, fan-in and ingest.

Membership test: the code chooses or assembles implementations for one pod. `env.py` is
the only reader of the environment, `stage_ref.py` the only import by string, and
`local.py` the only importer of `ag.adapters.fakes`.
"""
