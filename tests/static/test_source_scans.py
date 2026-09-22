"""The two static scans of `tools/scan_sources.py`, as tests.

What: `src/ag` has no environment read outside `runtime/env.py` and no import by string
outside `runtime/stage_ref.py`; and each rule fires on the code it is meant to catch.

Why: a scan over a nearly empty tree passes whether or not its rules work. The
`test_rule_fires_on_*` cases are the break-it-once evidence, kept as tests so the rules
stay proven after the tree fills.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))

import scan_sources  # noqa: E402

AG = REPO / "src" / "ag"


def test_tree_is_clean() -> None:
    findings = scan_sources.scan_tree(root=AG)
    assert [found.render() for found in findings] == []


def test_every_allowlisted_file_exists() -> None:
    assert scan_sources.missing_allowlisted_files(root=AG) == []


@pytest.mark.parametrize(
    "source",
    [
        "import os\nvalue = os.environ['AG_X']\n",
        "import os\nvalue = os.getenv('AG_X')\n",
        "import os as operating_system\nvalue = operating_system.environ\n",
        "from os import environ\n",
        "from os import getenv\n",
    ],
)
def test_rule_fires_on_environment_read(source: str) -> None:
    findings = scan_sources.scan_source(source=source, path="probe.py")
    assert [found.rule for found in findings] == [scan_sources.ENVIRONMENT_READ]


@pytest.mark.parametrize(
    "source",
    [
        "import importlib\n",
        "import importlib.metadata\n",
        "from importlib import import_module\n",
        "from importlib.metadata import version\n",
        "import runpy\n",
        "module = __import__('ag.runtime')\n",
    ],
)
def test_rule_fires_on_import_by_string(source: str) -> None:
    findings = scan_sources.scan_source(source=source, path="probe.py")
    assert [found.rule for found in findings] == [scan_sources.IMPORT_BY_STRING]


@pytest.mark.parametrize(
    "source",
    [
        "import os\npath = os.path.join('a', 'b')\n",
        "import os\nenviron = {}\nvalue = environ['AG_X']\n",
        "from pathlib import Path\n",
        "import importlib_resources\n",
        "def load(name: str) -> None:\n    return None\n",
    ],
)
def test_rules_stay_quiet_on_lookalikes(source: str) -> None:
    assert scan_sources.scan_source(source=source, path="probe.py") == []


@pytest.mark.parametrize(
    ("rule", "allowed_file", "source"),
    [
        (
            scan_sources.ENVIRONMENT_READ,
            "runtime/env.py",
            "import os\nvalue = os.environ['AG_X']\n",
        ),
        (
            scan_sources.IMPORT_BY_STRING,
            "runtime/stage_ref.py",
            "import importlib\n",
        ),
    ],
)
def test_scan_tree_exempts_only_the_allowlisted_file(
    tmp_path: Path, rule: str, allowed_file: str, source: str
) -> None:
    for relative in (allowed_file, "generalization/operations/probe.py"):
        file = tmp_path / relative
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(source, encoding="utf-8")

    findings = scan_sources.scan_tree(root=tmp_path)

    assert [(found.path, found.rule) for found in findings] == [
        ("generalization/operations/probe.py", rule)
    ]


def test_allowlist_exempts_only_its_own_file() -> None:
    allowed = scan_sources.ALLOWLIST[scan_sources.ENVIRONMENT_READ]
    assert "runtime/env.py" in allowed
    assert "runtime/stage_ref.py" not in allowed
    allowed = scan_sources.ALLOWLIST[scan_sources.IMPORT_BY_STRING]
    assert "runtime/stage_ref.py" in allowed
    assert "runtime/env.py" not in allowed
