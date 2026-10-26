# Goal: Align DuckDB SQL error column offsets when multiple `{...}` interpolations precede a syntax error

## Context & Goal
When `_parse_sql_duckdb` sanitizes `{...}` Python interpolations in a SQL query, `idx_to_offset_dict` records each replacement index `idx` in the *original* SQL string and the added quote length `offset`. However, DuckDB's `error_line_start` and `position` are in the *sanitized* SQL coordinate system. Comparing `error_line_start <= idx < position` directly against the unadjusted `idx` miscalculates the error column offset whenever earlier `{...}` interpolations shift the sanitized positions.

## Acceptance Criteria
- Track `preceding_offset = 0` while iterating `for idx, offset in idx_to_offset_dict.items():`, compute `sanitized_idx = idx + preceding_offset`, increment `preceding_offset += offset`, and check `if error_line_start <= sanitized_idx < position:` when accumulating `cumulative_offset`.
