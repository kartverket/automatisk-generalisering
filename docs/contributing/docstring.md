# Docstring standard

Code should aim to be self-documenting. Descriptive naming, clear structure, and single-responsibility design reduce the need for heavy documentation. Docstrings are supplementary and should focus on intent rather than repeating what the code already expresses.

If a method requires many inline comments to explain its flow, that is often a useful design signal. It may indicate that the logic could be split into smaller functions or that naming can be improved. Prioritizing clear structure reduces the need for inline explanations.

### 1. Document "What" it does
Every function or method should include a brief description of what it does.
In many cases with descriptive naming and well structured code, one or two sentences explaining “What” it it does can be sufficient.

Use additional detail only when the purpose is not immediately clear or when the function plays a meaningful role in the overall workflow.


### 2. Document “How” selectively
Include a How section only when:

- The logic is non-obvious
- The function orchestrates several steps
- Understanding the flow matters for maintainers

Many functions do not require a How section.

Orchestration methods (such as `main`, `run`, or other entry-point functions) often require a
How section. These functions typically coordinate several steps, call multiple helpers, or
manage workflow sequencing, and documenting that flow helps future maintainers understand the
overall structure. Even when each individual step is clear, the orchestration itself usually
benefits from a brief How explanation.

### 3. Document “Why” when context matters
Add a Why section when:

- A design decision is not immediately clear,
- A tradeoff or assumption should be communicated, or
- Maintainers need background to understand the reasoning.

If no such context exists, omit this section.


### 4. Args/Returns are optional

These sections are helpful when:

- Parameter meaning isn’t obvious from type hints and names,
- A return value carries contextual meaning,
- Or the function is part of a public callable interface where clarity is important.

When type hints and descriptive naming already communicate the intent, these sections can be omitted.

### 5. Avoid documenting what the code already expresses

Docstrings should not restate implementation details or obvious behavior.
If the code is clear, keep the documentation minimal to avoid unnecessary noise.

## Example docstring format
The two examples below illustrate when different levels of structure are appropriate:

- The first shows a simple case where a short description is enough.  
- The second shows the formatting to use when additional sections (How, Why, Args, Returns) are helpful.  
Use the extra sections only when needed; otherwise, keep the docstring brief.

```python
def example_function(param: int) -> str:
    """
    Short description of the function's purpose.
    """
```

```python
def example_function(param: int) -> str:
    """
    What:
        Short description of the function's purpose.

    How:
        Only include this section if the flow is non-obvious
        or the function orchestrates several steps.

    Why:
        Include only when design choices or assumptions
        need to be communicated.

    Args:
        param (int): Describe the meaning only if it is not obvious.

    Returns:
        str: Describe the return value only if it carries context.
    """
```

---
### Navigation

- [Contribution Guide](index.md)
- [Return to README](../../README.md)
