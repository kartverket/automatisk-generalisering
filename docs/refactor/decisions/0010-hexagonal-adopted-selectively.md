# ADR-0010: Hexagonal adopted selectively for a batch geoprocessing domain

**Status:** Accepted

## Context

Ports-and-adapters and the surrounding Python literature — chiefly Percival & Gregory,
*Architecture Patterns with Python* — assume a request-serving application with a
transactional store. This system is batch geoprocessing: no users, no requests, no
transactional store, no concurrency within a pod, one sequential executor.

Adopting the pattern wholesale would import machinery with nothing to do.

## Decision

Adopt ports, adapters, composition roots, contract tests and fakes. Reject the store-oriented
and application-oriented patterns, and record the rejections.

Rejected:

| pattern | why not |
|---|---|
| Repository, Unit of Work | no transactional aggregate store. The geodatabase is the store; the pod is the unit of work |
| DDD entities and aggregates | domain objects are feature classes on disk, not in-memory object graphs |
| a service layer above operations | operations are the use cases |
| message bus, domain events, CQRS | one sequential executor, one writer per object |
| a formal primary port | one driving actor with no plan for a second |

## Consequences

Adopted decisions rest on domain-specific grounds, not textbook ones, and must be revisited on
those grounds:

- Ports are split by measured call-site frequency, not by "one reason to change". The port
  boundary tracks a vendor library's surface, not a use case.
- Ports are coarse (25–35 methods). Interface segregation applies when clients depend on
  different subsets; here every operation potentially uses any geometry method and all
  adapters are constructed together. This weakens the textbook pressure behind Q-B, which must
  be settled by measurement rather than by ISP.
- Fakes over mocks, because the real dependency is licensed, Windows-adjacent and slow.

Ranked honestly: the K-invariance harness is the most valuable correctness mechanism in the
system, and it is not a hexagonal artifact. Partition correctness is data-shaped and no
architecture pattern addresses it. The architecture makes the harness cheap to run by making
`tests/invariance/` a driving adapter; it does not make the system correct.

A future reader who notices the missing Repository should read this before adding one.
