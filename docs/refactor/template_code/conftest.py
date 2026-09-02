"""Puts this directory on `sys.path` so `ag.*` resolves.

TEMPLATE — not shipped. The real distribution is installed, so `ag` resolves from the
installed package and no path manipulation exists (03-architecture §7.1). Here the
tree is documentation that happens to run, so it needs one line of help.

pytest imports this automatically for anything under `tests/`; `tools/*.py` do the
same thing inline.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
