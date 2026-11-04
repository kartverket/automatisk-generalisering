# ADR-0017: Row shape, the declared grammar of port outputs

**Status:** Accepted, 2026-10-19.

**Scope:** `ag/ports/row_shape.py`, `ag/ports/columns.py`, every port Protocol in
`ag/ports/`, and the checks over them in `tests/static/`. Absorbs A12.1, A12.2, A12.3,
A12.4, A12.5 and A12.5a. Two items join later: the call-site declaration for writes
(A12.7a), with its declaration type; the in-place mutators (A12.6), with their declaration
form. The lineage side of the grammar, what the facade does with a declaration and with a
parents table, belongs to the lineage design and is not here.

Related: ADR-0018 AR-3 (ports are Protocols), ADR-0020 OP-1 (the declaration is the
signature), ADR-0021 ST-2 (stage inputs: role and spatiality; section RS-2 relates to it).

## Direction

1. A port output's row shape is declared on two independent axes, cardinality (`ONE`,
   `MANY`, `GROUP`) and ids (`CARRY`, `MINT`, `FOREIGN`), never as a single enum.
2. Three cells are illegal, each for a stated reason. `GROUP + CARRY` and
   `GROUP + FOREIGN`: many parents, one row, and a scalar cannot hold a set.
   `MANY + CARRY`: the inheritance model lineage rejects, since five pieces keeping one id
   leave the log unable to express a partial drop. `CARRY` implies `ONE`.
3. Every output names the input its rows derive from: the subject for `CARRY` and `MINT`,
   the inputs its ref columns name for `FOREIGN`. Only the subject carries identity into an
   output; a context influences the output without contributing identity. This relates to,
   and is not the same as, the stage-level input roles of ADR-0021 ST-2.
4. The declaration lives on the port Protocol, is read from the Protocol and never from an
   adapter, and leaves the method's structural type untouched, so adapters conform without
   decoration.
5. Writes whose rows the caller builds are a category of the grammar: their ids axis is
   declared at the call site, not by an entry on the Protocol. The category's rules join
   this ADR with the declaration type.
6. The parents out-param of a `MINT` method is exempt from the grammar: it is a relation
   the layer above consumes, not a row-shaped output.
7. Every `Out` parameter of every port method is declared, and a check over the whole
   surface rejects what construction cannot, so forgetting is impossible.

## RS-1 The two axes

**Direction.** Cardinality says how many output rows one subject row yields; ids says what
identity those rows carry. The axes are independent and are declared together.

**Details.**

- **RS-D1** The members: `ONE`, `MANY`, `GROUP`; `CARRY` keeps the subject's id, `MINT`
  issues new ids with the edges from the subject's rows recorded, `FOREIGN` carries no
  `lineage_id` and holds subject ids in declared columns.
- **RS-D2** No value is named `TRANSFORM`: that word is a runtime-derived edge kind, and
  reusing it would blur declared against derived.
- **RS-D3** Cost is stated at the declaration: `ONE + MINT` emits one edge per row, the most
  expensive shape in the system, against one edge per group for `GROUP + MINT` and none for
  `ONE + CARRY`. Legal, but a deliberate choice, or it becomes the default for anything
  that feels transformative and log volume grows on the wrong axis.
- **RS-D4** Per-row behaviour comes from the parents table, not from the declaration: a
  group with one parent carries the id and emits no edge, a group with two or more mints;
  the same for `MANY`. Methods that are mostly 1:1 in practice cost almost nothing. This is
  runtime behaviour inside a cell, not an argument for legalising `GROUP + CARRY`.
- **RS-D5** `Rows` refuses the three illegal cells, a `CARRY` or `MINT` without a subject,
  and a `FOREIGN` with a subject or without refs, at construction, so a wrong declaration
  fails when the Protocol is imported.

## RS-2 Subject, context and refs

**Direction.** Every output names the input its rows derive from. Only the subject carries
identity into an output; a context influences without contributing identity; for `FOREIGN`
the ref columns name the subject inputs in place of a subject.

**Details.**

- **RS-D6** `intersection` output rows are pieces of the roads; the overlay influenced the
  result without contributing identity. Declaring both as subjects would make every admin
  polygon an ancestor of every road piece.
- **RS-D7** A port subject may be fed from a `CONTEXT` stage input: the displacement
  feature is buffered from context roads. A port context may be fed from a
  `PROCESSING`-derived intermediate: `propagate_displacement` reads that feature as
  `context` and the simplified buildings as `subject`. What holds at both levels: only the
  subject carries identity into outputs (ADR-0021 ST-D21).
- **RS-D8** The word `context` is shared with the stage role because both mean "influences,
  never becomes", and for no other reason.
- **RS-D9** `refs` maps a ref column to the subject input whose ids it holds and replaces
  `subject=` for `FOREIGN`. A null in a ref column is legitimate data, such as a spatial
  join with no match.

## RS-3 Where the declaration lives

**Direction.** On the Protocol method, keyed by the output parameter's name, read from the
Protocol and never from an adapter instance, and never changing the method's structural
type.

**Details.**

- **RS-D10** `@row_shape(**outputs)`, keyed by the `Out` parameter's name, stores the
  mapping as `__row_shape__` on the Protocol function and returns the function unchanged.
  The lineage facade reads it from the Protocol class.
- **RS-D11** Every port handle parameter carries exactly one of `In`, `Out`, `Mutates` and
  `ParentsOut`, written with the signature; a parameter-name convention is not used.

## RS-4 The check over the surface

**Direction.** Every `Out` is declared and every declaration is well-formed, enforced by a
static test over every port Protocol, with each rule broken once.

**Details.**

- **RS-D12** The rules: every `Out` has a row; every row names an `Out`; subject, context
  and refs name `In` parameters; both axes are present; `CARRY` and `MINT` have a subject;
  `FOREIGN` has refs and no subject; the three illegal cells are refused with their
  reasons; `ParentsOut` is exempt and carries no row; a handle parameter without a marker
  fails, walking `Annotated`, unions, tuples and sequences; a method with no `Out` is in an
  explicit query list or fails; a `Mutates` parameter fails closed until its declaration
  form is decided.
- **RS-D13** Two things no rule sees, stated so they are not mistaken for omissions: a
  handle inside a `Spatial` predicate is a value, outside any marker; a method that changes
  its input in place has no output to declare, and a join on a non-unique key would change
  row count with nothing to declare it; open until the in-place mutators join.
- **RS-D14** Where: `tests/static/test_row_shape.py` over every Protocol in `ag/ports/`,
  and `tests/static/test_row_shape_typing.py` for the structural-type guard, which runs
  pyright on a fixture it writes. Each rule has a case in `tools/break_once/cases/`.

## RS-5 Writes declared at the call site

**Direction.** An `Out` whose rows the caller builds is declared where the method is
called, not by an entry on the Protocol; the form arrives with the declaration type.

**Details.**

- **RS-D15** No such method is on the surface yet. Until the declaration type exists, an
  `Out` with no entry fails RS-D12; once it exists, the check identifies the declaring
  parameter by that type, and an `Out` declared at the call site has no `@row_shape` entry
  while an `Out` with an entry has no call-site keyword.

## RS-6 Parents

**Direction.** The parents out-param is exempt from the grammar; what it reports and how
the layer above uses it belong to the lineage design.

**Details.**

- **RS-D16** The marker is `ParentsOut`; the check exempts it (RS-D12); its columns are
  `PARENT_ID` and `CHILD_ID` in `ports/columns.py`.

## Rejected

- **RS-R1** A single shape enum (`PRESERVE`, `COLLAPSE`, `SPLIT`, `NONE`, later `REFERENCE`
  and `EXPAND`). Rejected because `ONE + MINT` is a real declarable judgement a single enum
  had no cell for, and the special cases folded into the grid: `REFERENCE` became
  `ids=FOREIGN` and `EXPAND` became `MANY + FOREIGN`. Reopened by a shape the grid cannot
  express.
- **RS-R2** A `NONE` member for outputs with no subject. Rejected because the surface has no
  genuine aggregate output, and an escape hatch becomes the default. Reopened by a genuine
  aggregate output argued on its merits; re-adding the member is one line.
- **RS-R3** Legalising `GROUP + CARRY` because most groups have one parent. Rejected because
  per-row behaviour is runtime behaviour inside a cell (RS-D4), and the declaration must
  cover the group with two parents. Reopened by nothing short of a new identity model.
- **RS-R4** Per-method wrappers implementing the Protocol. Rejected: about forty delegating
  methods, two implementations of one Protocol free to drift, easy to use wrongly. Reopened
  by a method whose lineage handling cannot be derived from its declaration by the generic
  facade.
- **RS-R5** Marking handle parameters by a name convention, or by "named by some
  declaration". Rejected because names are not checked, and a declaration-derived rule
  misses the undeclared output, which is the case the check exists for. Reopening this
  changes Direction 7.
- **RS-R6** A sentinel entry in `@row_shape` for a call-site-declared write. Rejected because
  the call-site value names handles, not parameters, so it is a different type, and a
  sentinel would widen `__row_shape__` for every reader. Reopened by the call-site
  declaration becoming a `Rows` value.
