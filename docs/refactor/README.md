# Refactor documentation

The design record for moving cartographic generalization onto Kubernetes behind a port and
adapter boundary. Being implemented under `src/ag` slice by slice
(`temp/findings/implementation_plan.md`); every slice updates these documents in the same pull
requests as its code, and they move out of `docs/refactor/` once their content has landed (plan
§4.8).

Read [terminology](../terminology.md) first — several everyday words mean something
specific here, and two of them (`workspace`, `container`) mean the opposite of the obvious
reading.

## Documents

| doc | owns | status | graduates when |
|---|---|---|---|
| [template_code](template_code/README.md) | a learning pass, reviewed in `temp/findings/template_review.md`; the source for lifts into `src/ag`, one module per slice | TEMPLATE, not promoted | its last module has been lifted or dropped; then **deleted** |
| [terminology](../terminology.md) | the vocabulary, the collisions, the retired words | TARGET | the identifiers exist in `src/ag/`; then it becomes the vocabulary reference |
| [02-runtime](02-runtime.md) | how the system executes — declarations, derivation, storage scopes, legality, partition correctness, validation | TARGET | `src/ag/core/` and `src/ag/runtime/` exist and a stage runs end to end on the cluster |
| [03-architecture](03-architecture.md) | how the code is structured — boundary, ports, layering, helpers, observability, failure | TARGET | `.importlinter` exists and passes in CI, and one port has an adapter plus contract tests |
| [04-migration](04-migration.md) | what changes in the current codebase, in what order, and the measurements | TARGET | never — **deleted** on completion, not graduated |
| [decisions](../decisions/README.md) | the themed ADRs, the source of truth for direction | — | moved to `docs/decisions/` on 2026-10-22 |

Every document carries a `Status` / `Owns` / `Does not own` / `Graduates when` header. The
`Owns` pair is load-bearing: the one contradiction these documents have actually produced arose
where two of them described the same thing and neither declared which was authoritative.

## Conventions

- ADRs are referenced by number and id ("ADR-0019 PC-D5"), never by path; they live in
  `docs/decisions/`, and `tests/static/test_adr_citations.py` resolves every citation.
- ADR numbers are never reused or renumbered. Section numbers rot; ADR ids do not.
- Cross-document references are markdown links to heading anchors, never bare section
  numbers.
- Design documents keep two sentences and a link where an ADR exists. The argument lives in
  the ADR — that is what stops these documents growing every time someone asks a question.

## Sources

The sources the ADRs cite are in `docs/decisions/README.md`. Kept here for 03-architecture §8:

- Kubernetes 1.31, *Pod failure policy for Jobs goes GA* —
  https://kubernetes.io/blog/2024/08/19/kubernetes-1-31-pod-failure-policy-for-jobs-goes-ga/

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

**3. Reciprocal banners on the current-state documents.** *Done in slice 0 (2026-09-22): the
first sentence of the banner only; the CURRENT documents do not point here.* `docs/developer_reference/` describes
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

**4. Create `docs/README.md`.** *Done in slice 0 (2026-09-22), indexing `setup/`, `contributing/`
and `developer_reference/` only; it does not index this directory.* There is no index above `docs/`, so the current/target split is
invisible from the top. One table: `setup/`, `contributing/`, `developer_reference/` (current),
`refactor/` (target), `archive/` (historical).

**5. Add a markdown link checker to CI.** Every cross-reference in `docs/refactor/` is now a
link to a heading anchor. Anchors break silently when a heading is edited, and this restructure
created roughly forty of them. `lychee` or `markdown-link-check` over `docs/**/*.md`, in
`.github/workflows/`.

**6. Move `decisions/` to `docs/decisions/` at first graduation.** *Done 2026-10-22, with the
consolidation into themed ADRs.* ADRs outlive the refactor;
they are referenced by number precisely so this move costs nothing. Do it when the first
document graduates, not before.
