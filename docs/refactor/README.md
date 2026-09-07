# Refactor documentation

The target design for moving cartographic generalization onto Kubernetes behind a port and
adapter boundary. Nothing here is implemented.

Read [01-terminology](01-terminology.md) first — several everyday words mean something
specific here, and two of them (`workspace`, `container`) mean the opposite of the obvious
reading.

## Documents

| doc | owns | status | graduates when |
|---|---|---|---|
| [template_code](template_code/README.md) | the design as runnable, type-checked Python; the source tree made checkable | TEMPLATE | `src/ag/` exists; `ag/` moves there wholesale and this is **deleted** |
| [01-terminology](01-terminology.md) | the vocabulary, the collisions, the retired words | TARGET | the identifiers exist in `src/ag/`; then it becomes the vocabulary reference |
| [02-runtime](02-runtime.md) | how the system executes — declarations, derivation, storage scopes, legality, partition correctness, validation | TARGET | `src/ag/core/` and `src/ag/runtime/` exist and a stage runs end to end on the cluster |
| [03-architecture](03-architecture.md) | how the code is structured — boundary, ports, layering, helpers, observability, failure | TARGET | `.importlinter` exists and passes in CI, and one port has an adapter plus contract tests |
| [04-migration](04-migration.md) | what changes in the current codebase, in what order, and the measurements | TARGET | never — **deleted** on completion, not graduated |
| [decisions/](decisions/) | one accepted decision per file, Nygard format | — | ADRs are immutable; supersede with a new ADR rather than editing |

Every document carries a `Status` / `Owns` / `Does not own` / `Graduates when` header. The
`Owns` pair is load-bearing: the one contradiction these documents have actually produced arose
where two of them described the same thing and neither declared which was authoritative.

## Conventions

- ADRs are referenced by number ("ADR-0005"), never by path, so `decisions/` can move to
  `docs/decisions/` at first graduation without breaking references.
- ADR numbers are never reused or renumbered. Section numbers rot; ADR ids do not.
- Cross-document references are markdown links to heading anchors, never bare section
  numbers.
- Design documents keep two sentences and a link where an ADR exists. The argument lives in
  the ADR — that is what stops these documents growing every time someone asks a question.

## Decisions

| ADR | decision |
|---|---|
| [0001](decisions/0001-selection-is-a-predicate-value.md) | Selection is a composable predicate value, not a held selection |
| [0002](decisions/0002-three-geoprocessing-ports.md) | Three geoprocessing ports rather than one or many |
| [0003](decisions/0003-scratchhandle-at-the-port-boundary.md) | `ScratchHandle`, not `DataObject`, at the port boundary |
| [0004](decisions/0004-geometry-value-type-no-cursor.md) | `Geometry` as a value type; no cursor in the port |
| [0005](decisions/0005-helpers-package-name.md) | `helpers/` as the package name |
| [0006](decisions/0006-logging-is-not-a-port.md) | Logging is not a port |
| [0007](decisions/0007-ports-are-protocol-not-abc.md) | Ports are `Protocol`, not `ABC` |
| [0008](decisions/0008-toolbox-passed-explicitly.md) | `Toolbox` passed explicitly, not ambient |
| [0009](decisions/0009-no-intra-pod-resume.md) | No intra-pod resume; the stage is the resume granularity |
| [0010](decisions/0010-hexagonal-adopted-selectively.md) | Hexagonal adopted selectively for a batch geoprocessing domain |
| [0011](decisions/0011-operation-decorator-and-handle-namespaces.md) | Declarations come from signatures and class attributes, not from strings |
| [0012](decisions/0012-identities-are-declared-centrally.md) | Sources and products are declared once, centrally, as symbols |
| [0013](decisions/0013-tuning-is-base-plus-one-delta.md) | Tuning is base plus one delta, with no resolution mechanism |

**0001–0010** were extracted in one pass from design documents written earlier, not argued one at
a time over months — read them as the reasoning behind a single design, not as a decision log.

**0011–0013** were argued individually, against working code, and each supersedes something the
design documents said. 0012 in particular supersedes
[02-runtime §2.2](02-runtime.md#22-data-objects) on how identities are declared.

An ADR is warranted when a developer joining after the first commit would ask "why is it like
this?" *and* the decision constrains future work enough that someone might try to overturn it.
A choice settled before any code existed, whose outcome is now simply what the system is,
fails the first test — naming, layout and formatting decisions usually do. Those are one line
in the document that owns the subject.

## Sources

Kept because several decisions cite them and the citations should be checkable.

- Cockburn, *Hexagonal Architecture* — https://alistair.cockburn.us/hexagonal-architecture
- PEP 544, *Protocols: Structural subtyping* — https://peps.python.org/pep-0544/
- OGC *Common Query Language (CQL2)* — https://docs.ogc.org/is/21-065r2/21-065r2.html
- Kubernetes 1.31, *Pod failure policy for Jobs goes GA* —
  https://kubernetes.io/blog/2024/08/19/kubernetes-1-31-pod-failure-policy-for-jobs-goes-ga/
- import-linter — https://import-linter.readthedocs.io/en/stable/
- Percival & Gregory, *Architecture Patterns with Python* (O'Reilly)

---

## Recommended actions outside docs/refactor/ (not performed)

Each is a concrete change outside this directory, left for the user to apply.

**1. Archive the superseded design documents.** These predate the current design and are wrong
in places a reader cannot detect from inside them. `02-runtime` and `03-architecture` no longer
reference them.

```
mkdir -p docs/archive
git mv file_seames_discussion/file_seams_design_note.md          docs/archive/
git mv file_seames_discussion/orchestrator_dag_handoff.md        docs/archive/
git mv file_seames_discussion/orchestrator_filemanager_handoff.md docs/archive/
```

Add to the top of each archived file:

```markdown
**Status:** SUPERSEDED — historical. Do not use.
Superseded by docs/refactor/02-runtime.md and docs/refactor/03-architecture.md.
```

`file_seames_discussion/refactor_plan_old.md` was named as superseded but does not exist in
the working tree; if it appears in a branch, archive it the same way.

**2. Move or archive the remaining `file_seames_discussion/` contents.** The directory name is
a typo (`seames`) and its contents are now split three ways:

- `design_reference.md`, `refactor_plan.md` — superseded by `docs/refactor/02-runtime.md` and
  `docs/refactor/03-architecture.md`. Archive with the banner above.
- `code_template_example/` — **done**, now `docs/refactor/template_code/`, laid out to mirror
  03-architecture §7. `orchestrator_dag_reference.py` is still outside and unclassified.
  `code_template_example/vector_test_example/` was left in place: it is a separate,
  self-contained example with its own README, contracts and tests, and needs its own decision.
- `platform_team_questions.md` — live external unknowns, cited by 02-runtime. Suggested:
  `docs/refactor/platform-questions.md`.
- `plan_summary.md`, `package_rationale.md` — not classified in this restructure and not read
  during it. Review before archiving.

**3. Reciprocal banners on the current-state documents.** `docs/developer_reference/` describes
the system as it is today; the refactor documents describe the target. Neither says so, and
both are reachable from a search.

Add to `docs/developer_reference/index.md`, `project_structure.md`,
`io_and_file_management.md`, `runtime_entrypoints.md` and `design_and_conventions.md`:

```markdown
**Status:** CURRENT — describes the system as implemented.
The target design is docs/refactor/. Where they differ, this file describes today.
```

Add to `docs/refactor/README.md` in return once the above exists — a line pointing at
`docs/developer_reference/` as the current-state counterpart.

**4. Create `docs/README.md`.** There is no index above `docs/`, so the current/target split is
invisible from the top. One table: `setup/`, `contributing/`, `developer_reference/` (current),
`refactor/` (target), `archive/` (historical).

**5. Add a markdown link checker to CI.** Every cross-reference in `docs/refactor/` is now a
link to a heading anchor. Anchors break silently when a heading is edited, and this restructure
created roughly forty of them. `lychee` or `markdown-link-check` over `docs/**/*.md`, in
`.github/workflows/`.

**6. Move `decisions/` to `docs/decisions/` at first graduation.** ADRs outlive the refactor;
they are referenced by number precisely so this move costs nothing. Do it when the first
document graduates, not before.
