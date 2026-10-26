# Goal: Preserve underscores inside inline code spans when converting Markdown docstrings (`MarkdownConverter`)

## Context & Goal
When converting docstrings that are already plain Markdown containing backtick code spans (e.g. ``Use `shout_factor` ``) without structured RST/Google/NumPy docstring sections, default docstring converters escape underscores inside backtick spans (`shout\_factor`).

## Acceptance Criteria
- Add a `MarkdownConverter` class (with `priority = 0`, `can_convert(self, docstring: str) -> bool` matching unescaped closed backtick code spans across single or multiple lines, and `convert(self, docstring: str) -> str` returning `docstring` unchanged) right after `MarimoConverter`.
