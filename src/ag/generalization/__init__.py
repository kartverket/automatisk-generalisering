"""All cartographic domain code: sources, products, classification rules, the pipeline
registry, tuning, helpers, operations and pipelines.

Membership test: the code states a cartographic fact or a processing step for a map
object. It may not import `ag.adapters`, `ag.staging`, `ag.runtime`, `ag.orchestrator`
or `ag.lineage`. Inside it the layers run `registry` over `pipelines` over `operations`
over `helpers` over the leaf modules.
"""
