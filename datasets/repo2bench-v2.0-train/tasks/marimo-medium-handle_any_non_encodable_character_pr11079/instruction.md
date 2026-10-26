# Goal: Handle arbitrary non-encodable Unicode characters in CLI `echo` fallback on non-UTF-8 streams

## Context & Goal
When `marimo convert` or `marimo check` prints output via `echo(*args, **kwargs)` on a non-UTF-8 terminal (such as Windows `cp1252`), `echo` catches `UnicodeEncodeError` and replaces six known characters (`→ ← ✓ ✗ • …`) with ASCII equivalents. However, if the text contains any other character outside the stream's encoding (such as a Unicode minus sign `−` or emoji), the retry inside the `except UnicodeEncodeError:` block raises `UnicodeEncodeError` again and crashes the CLI.

## Acceptance Criteria
1. When `UnicodeEncodeError` occurs in `echo()`, after replacing the six known symbols (`→` -> `->`, `←` -> `<-`, `✓` -> `v`, `✗` -> `x`, `•` -> `*`, `…` -> `...`), determine the target stream's encoding (`kwargs.get("file")`, or `sys.stderr` if `kwargs.get("err")` else `sys.stdout`, defaulting to `"ascii"`) and backslash-escape any remaining unencodable characters using `.encode(encoding, errors="backslashreplace").decode(encoding)`.
