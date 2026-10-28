# Task: Preserve underscores in docstring code spans (`MarkdownConverter`)

## Problem Description
In `marimo/_utils/docs.py`, when `pylsp_markdown` converts docstrings that are plain Markdown containing inline backtick code spans (e.g. ``Use `shout_factor` or `a_b` ``) without structured RST/NumPy/Google sections, upstream converters escape underscores inside backtick spans.

## Requirements
1. In `marimo/_utils/docs.py`, add a `MarkdownConverter` class right after `MarimoConverter` with:
   - `priority = 0`
   - `can_convert(self, docstring: str) -> bool`: returns `True` when `re.search(r"(?<![\\`])(`+)(?!`)(.+?)(?<!`)\1(?!`)", docstring, flags=re.DOTALL) is not None`
   - `convert(self, docstring: str) -> str`: returns `docstring` verbatim.
