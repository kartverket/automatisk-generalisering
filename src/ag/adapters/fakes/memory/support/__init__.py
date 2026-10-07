"""Store-bound code that more than one method group of the in-memory adapter needs.

Membership test: a second group module needs it, for example the pair rules of the MINT
methods or duplicate-field naming. A support module never imports a group module or a
port package.
"""
