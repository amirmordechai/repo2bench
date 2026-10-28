# Goal: Escape square brackets in web component attribute values (`_build_attr`) so Markdown links do not corrupt widgets

## Context & Goal
When a Marimo UI element or web component is embedded inside Markdown (`mo.md`), `_build_attr(name, value)` escapes backslashes (`&#92;`) and dollar signs (`&#36;`) so LaTeX and escape sequences do not corrupt `data-*` attributes. However, unescaped square brackets (`[` and `]`) in values like `"C[A](C)"` or `"[a][b]"` are parsed as Markdown links, breaking widget initialization.

## Acceptance Criteria
- Update `_build_attr` so `[` is replaced with `"&#91;"` and `]` is replaced with `"&#93;"` in the serialized attribute value alongside `$` and `\`.
