# Output Modes

## HTML Mode

Use HTML mode when the user needs:

- Click-through interactive prototypes
- Browser preview
- Page-to-page navigation demo
- Lightweight deliverables for review

Pipeline:

`requirements -> page_spec -> HTML pages`

Typical output:

- `prototypes/index.html`
- `prototypes/*.html`
- `prototypes/common.css`

## draw.io Mode

Use draw.io mode when the user needs:

- Wireframes for review or handoff
- Structured diagram deliverables
- Multi-page swimlane layouts
- Strong validation and consistency gates

Pipeline:

`page_model -> build_page_spec.py -> render.py -> validate.py -> merge.py`

Typical output:

- `.prototype-generator/page_models/page_model_*.json`
- `.prototype-generator/page_specs/page_spec_*.md`
- `prototypes/[产品名称].drawio`

## Selection Heuristic

- If the user explicitly asks for `HTML`, use HTML mode
- If the user explicitly asks for `draw.io` / `drawio`, use draw.io mode
- If unspecified, clarify only when format materially affects delivery
