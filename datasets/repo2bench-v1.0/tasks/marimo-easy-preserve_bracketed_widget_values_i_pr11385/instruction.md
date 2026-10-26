# Task: Preserve bracketed widget values in Markdown (`_build_attr`)

## Problem Description
In `marimo/_plugins/core/web_component.py`, `_build_attr(name: str, value: JSONType) -> str` escapes `\` (`&#92;`) and `$` (`&#36;`) so widget attributes embedded inside Markdown are not corrupted by Markdown or LaTeX parsers. However, unescaped `[` and `]` inside attribute values (such as `"C[A](C)"` or `"[a][b]"`) are interpreted by the Markdown parser as Markdown links or reference links, corrupting the widget's `data-initial-value`.

## Requirements
1. Update `_build_attr` in `marimo/_plugins/core/web_component.py` to also replace `"[", "&#91;"` and `"]", "&#93;"` on `processed` before returning `f"data-{name}='{processed}'"`.
