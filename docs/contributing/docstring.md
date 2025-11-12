# Docstring standard

Code should aim to be self documenting, descriptive naming combined with single responsibility and DRY (Don't Repeat Yourself) should be a focus. Docstring documentation is supplementary. 

### Core rule
- Small, obvious functions: document **What only**.
- Callable entry points / complex logic: document **What** (always) + **How** and/or 
**Why** when they add information not obvious from the code.
- Modules/classes: give brief What; add How/Why only if it explains relationships, invariants, or usage intent.
- If you are unsure it is better to have more documentation rather than less.
- Docstring over comment.

### Decision guide 
- Always document **What**
- Add **How** when:
  - Non-trivial algorithmic approach or ordering matters.
  - The method is complex and does a lot of things, such that reading a summary of what it does would make the code more readable.
- Add **Why** when:
  - When the reason is not obvious. Or knowing the intention behind the method helps understand design decisions. 
