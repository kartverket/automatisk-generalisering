"""Engine-bound code that more than one method group of the ArcPy adapter needs.

Membership test: it may call the engine through the session, a second group module needs
it, and it is named for the engine artefact it handles, such as `pair_tables` or
`field_names`. A support module never imports a group module or a port package.
"""
