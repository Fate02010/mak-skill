# Quality Gates

## Core Rule

Never treat the final prototype file as the primary editing surface.
If quality fails, roll back to upstream structured artifacts.

## Required Gates

Before declaring success:

- `requirements/` exists
- `.prototype-generator/page_specs/` exists
- required compressed-doc artifacts exist when compression mode is active
- `validate.py` passes
- `check_prototype_consistency.py` passes

## draw.io-Specific Recovery

If draw.io output fails:

- First fix `.prototype-generator/page_specs/`
- If semantics are wrong, fix `page_model`
- Re-run render and merge
- Re-run module validation and final validation

Do not patch final `.drawio` as the default repair strategy.

## Context Discipline

When the project is large, the workflow must prefer:

`index.md -> overview -> module_brief -> module detail -> page_spec`

Do not carry the full source material through every step.
