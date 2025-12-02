# Design and Conventions
The design docs will be updated in the future.

### Design towards modularity
Strive towards these principles:
- **Single Single Responsibility:** Each function or method should do one clear thing. If a method needs many inline comments or has several logical phases, it may need to be split.
- **DRY:** "Do Not Repeat Yourselves". Avoid duplicating logic. Repeated patterns usually indicate that the code should be moved into a reusable helper or utility function.

### I/O Management Conventions
- All persistent files should be managed by `FileManager`
- Intermediate / scratch files should be managed by `WorkFileManager`

### Runtime Conventions
- Run `environment_setup` in the scope of the script.
- Use `PartitionIterator` to handle processing heavy logic on large data.


---
### Navigation

- [Developer Reference](index.md)
- [Return to README](../../README.md)
