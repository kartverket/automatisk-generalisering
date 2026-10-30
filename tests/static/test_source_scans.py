"""The static scans of `tools/scan_sources.py`, as tests.

What: each scope's tree is clean: `src/ag` has no environment read outside
`runtime/env.py` and no import by string outside `runtime/stage_ref.py`; the ArcPy
adapter root and `tests/support/arcpy` reach the engine through the session module or
inside its guard only. And each rule fires on the code it is meant to catch.

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

SCOPE_IDS = tuple(scan_sources.SCOPES)
ARCPY = scan_sources.ARCPY_SESSION_ONLY


def engine_findings(source: str) -> list[str]:
    findings = scan_sources.scan_source(source=source, path="probe.py", rules={ARCPY})
    return [found.rule for found in findings]


@pytest.mark.parametrize("scope_id", SCOPE_IDS)
def test_tree_is_clean(scope_id: str) -> None:
    findings = scan_sources.scan_tree(scan_sources.SCOPES[scope_id])
    assert [found.render() for found in findings] == []


@pytest.mark.parametrize("scope_id", SCOPE_IDS)
def test_every_allowlisted_file_exists(scope_id: str) -> None:
    assert scan_sources.missing_allowlisted_files(scan_sources.SCOPES[scope_id]) == []


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
    "source",
    [
        pytest.param("import arcpy.management\n", id="import-submodule"),
        pytest.param("from arcpy import management\n", id="from-arcpy-import"),
        pytest.param(
            "from arcpy.management import Delete\n", id="from-submodule-import"
        ),
        pytest.param("from arcpy import *\n", id="from-arcpy-import-star"),
    ],
)
def test_rule_fires_on_an_import_form_other_than_import_arcpy(source: str) -> None:
    assert engine_findings(source) == [ARCPY]


@pytest.mark.parametrize(
    "source",
    [
        pytest.param(
            "import arcpy\nFOUND = arcpy.Exists('x')\n", id="call-at-module-level"
        ),
        pytest.param(
            "import arcpy as engine\n\ndef f() -> bool:\n    return engine.Exists('x')\n",
            id="call-under-an-alias",
        ),
        pytest.param(
            "import arcpy\n\ndef f(run) -> None:\n    run(arcpy.Exists)\n",
            id="callable-passed-as-argument",
        ),
        pytest.param(
            "import arcpy\n\nclass A:\n    def __init__(self) -> None:\n"
            "        self.exists = arcpy.Exists\n",
            id="callable-bound-to-attribute",
        ),
        pytest.param(
            "import arcpy\n\ndef f():\n    return arcpy.Exists\n",
            id="callable-returned",
        ),
        pytest.param(
            "import arcpy\n\ndef f(path: str) -> None:\n"
            "    with open(path) as fh:\n        arcpy.Exists(fh.name)\n",
            id="with-block-that-is-not-the-guard",
        ),
        pytest.param(
            "import arcpy\n\ndef f(session) -> None:\n"
            "    with session.guard(arcpy.Describe('x')):\n        pass\n",
            id="reference-in-the-guard-call-itself",
        ),
        pytest.param(
            "import arcpy\n\ndef f(session) -> None:\n"
            "    with arcpy.da.Editor('w'), session.guard('x'):\n        pass\n",
            id="with-item-before-the-guard",
        ),
        pytest.param(
            "import arcpy\n\ndef f(session):\n    with session.guard('x'):\n"
            "        g = lambda: arcpy.da.SearchCursor('t', ['a'])\n    return g()\n",
            id="lambda-written-inside-the-guard",
        ),
        pytest.param(
            "import arcpy\n\ndef f(session):\n    with session.guard('x'):\n"
            "        def g():\n            return arcpy.da.SearchCursor('t', ['a'])\n"
            "    return g()\n",
            id="def-written-inside-the-guard",
        ),
        pytest.param(
            "import arcpy\n\ndef f(session, rows):\n    with session.guard('x'):\n"
            "        out = (arcpy.Point(*r) for r in rows)\n    return list(out)\n",
            id="generator-expression-written-inside-the-guard",
        ),
    ],
)
def test_rule_fires_on_reference_outside_guard(source: str) -> None:
    assert engine_findings(source) == [ARCPY]


@pytest.mark.parametrize(
    "source",
    [
        pytest.param(
            "import arcpy\n\ndef f(session):\n    with session.guard('x'):\n"
            "        return getattr(arcpy, 'management')\n",
            id="getattr-inside-guard",
        ),
        pytest.param(
            "import arcpy\n\ndef f(session):\n    with session.guard('x'):\n"
            "        setattr(arcpy.env, 'workspace', 'w')\n",
            id="setattr-inside-guard",
        ),
        pytest.param(
            "def f(o):\n    return hasattr(o, 'x')\n", id="hasattr-any-target"
        ),
        pytest.param("def f(o):\n    delattr(o, 'x')\n", id="delattr-any-target"),
        pytest.param("def f(o):\n    return vars(o)\n", id="vars-any-target"),
        pytest.param(
            "import arcpy\n\ndef f(session):\n    with session.guard('x'):\n"
            "        return arcpy.__dict__['management']\n",
            id="dunder-dict-inside-guard",
        ),
        pytest.param(
            "import arcpy\nfrom functools import reduce\n\ndef f(session):\n"
            "    with session.guard('x'):\n"
            "        return reduce(getattr, ['management', 'Delete'], arcpy)\n",
            id="getattr-passed-not-called",
        ),
        pytest.param(
            "import arcpy\nimport operator\n\ndef f(session):\n"
            "    with session.guard('x'):\n"
            "        return operator.attrgetter('management.Delete')(arcpy)\n",
            id="operator-attrgetter",
        ),
        pytest.param(
            "from operator import attrgetter as get\n",
            id="attrgetter-imported-under-alias",
        ),
        pytest.param("from operator import methodcaller\n", id="methodcaller-imported"),
        pytest.param(
            "def f(o):\n    return o.__getattribute__('x')\n", id="dunder-getattribute"
        ),
        pytest.param("import sys\n\nengine = sys.modules['arcpy']\n", id="sys-modules"),
        pytest.param(
            "import arcpy\n\ndef f(session):\n    with session.guard('x'):\n"
            "        try:\n            pass\n        except arcpy.ExecuteError:\n"
            "            pass\n",
            id="except-execute-error-inside-guard",
        ),
        pytest.param("from vendor import ExecuteError\n", id="execute-error-by-name"),
        pytest.param(
            "import arcpy\n\ndef f(session):\n    with session.guard('x'):\n"
            "        try:\n            pass\n        except (ValueError, arcpy.Error):\n"
            "            pass\n",
            id="except-on-an-engine-class-inside-guard",
        ),
    ],
)
def test_rule_fires_inside_the_guard_too(source: str) -> None:
    assert engine_findings(source) == [ARCPY]


@pytest.mark.parametrize(
    "source",
    [
        pytest.param("import arcpy\n", id="import-arcpy-alone"),
        pytest.param("import arcpy as engine\n", id="import-arcpy-as-alone"),
        pytest.param(
            "import arcpy\n\ndef f(session) -> None:\n"
            "    with session.guard('x'):\n        arcpy.Exists('x')\n",
            id="reference-inside-guard",
        ),
        pytest.param(
            "import arcpy\n\ndef f(session) -> None:\n"
            "    with session.guard('x'), arcpy.da.SearchCursor('t') as cursor:\n"
            "        next(cursor)\n",
            id="with-item-after-the-guard",
        ),
        pytest.param(
            "import arcpy\n\ndef f(cursor: arcpy.da.SearchCursor) -> arcpy.Result:\n"
            "    x: arcpy.Result = cursor\n    return x\n",
            id="annotations-only",
        ),
        pytest.param(
            "import arcpy\n\n\ndef f() -> None:\n    '''Mentions arcpy.Exists.'''\n",
            id="docstring-mention",
        ),
        pytest.param("arcpy = 1\nprint(arcpy)\n", id="name-without-the-import"),
        pytest.param("def f(o):\n    return o.modules['x']\n", id="modules-not-sys"),
    ],
)
def test_rule_stays_quiet_on_the_allowed_forms(source: str) -> None:
    assert engine_findings(source) == []


def test_findings_are_one_per_line_and_rule() -> None:
    source = "import arcpy\n\ndef f(o):\n    return getattr(arcpy, 'x'), arcpy.y\n"
    findings = scan_sources.scan_source(source=source, path="probe.py", rules={ARCPY})
    assert [(found.line, found.rule) for found in findings] == [(4, ARCPY)]


@pytest.mark.parametrize(
    ("scope_id", "rule", "allowed_file", "other_file", "source"),
    [
        pytest.param(
            "src-ag",
            scan_sources.ENVIRONMENT_READ,
            "runtime/env.py",
            "generalization/operations/probe.py",
            "import os\nvalue = os.environ['AG_X']\n",
            id="environment-read",
        ),
        pytest.param(
            "src-ag",
            scan_sources.IMPORT_BY_STRING,
            "runtime/stage_ref.py",
            "generalization/operations/probe.py",
            "import importlib\n",
            id="import-by-string",
        ),
        pytest.param(
            "adapters-arcpy",
            ARCPY,
            "session.py",
            "_base.py",
            "import arcpy\nFOUND = arcpy.Exists('x')\n",
            id="arcpy-session-only",
        ),
    ],
)
def test_scan_tree_exempts_only_the_allowlisted_file(
    tmp_path: Path,
    scope_id: str,
    rule: str,
    allowed_file: str,
    other_file: str,
    source: str,
) -> None:
    project = scan_sources.SCOPES[scope_id]
    for relative in (allowed_file, other_file):
        file = tmp_path / relative
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(source, encoding="utf-8")
    scope = scan_sources.Scope(
        root=tmp_path, rules=project.rules, allowlist=project.allowlist
    )

    findings = scan_sources.scan_tree(scope)

    assert [(found.path, found.rule) for found in findings] == [(other_file, rule)]


def test_the_test_support_scope_exempts_nothing() -> None:
    assert scan_sources.SCOPES["tests-support-arcpy"].allowlist == {}


def test_allowlist_exempts_only_its_own_file() -> None:
    allowlist = scan_sources.SCOPES["src-ag"].allowlist
    assert "runtime/env.py" in allowlist[scan_sources.ENVIRONMENT_READ]
    assert "runtime/stage_ref.py" not in allowlist[scan_sources.ENVIRONMENT_READ]
    assert "runtime/stage_ref.py" in allowlist[scan_sources.IMPORT_BY_STRING]
    assert "runtime/env.py" not in allowlist[scan_sources.IMPORT_BY_STRING]
    assert scan_sources.SCOPES["adapters-arcpy"].allowlist == {ARCPY: {"session.py"}}
