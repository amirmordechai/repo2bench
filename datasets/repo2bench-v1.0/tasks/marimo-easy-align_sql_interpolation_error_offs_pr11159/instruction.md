# Task: Align SQL interpolation error offsets in `_parse_sql_duckdb`

## Problem Description
In `marimo/_sql/parse.py`, inside `_parse_sql_duckdb`, `idx_to_offset_dict` maps bracket replacement indices `idx` in the *original* SQL string to the length `offset` of added quotes in the *sanitized* SQL string. However, DuckDB's `position` and `error_line_start` are in the *sanitized* SQL coordinate system! Comparing `error_line_start <= idx < position` directly against the unadjusted `idx` miscalculates `column_number` whenever multiple `{...}` interpolations appear before the error.

## Requirements
1. In `marimo/_sql/parse.py`, inside `_parse_sql_duckdb`:
   - Track `preceding_offset = 0` while iterating `for idx, offset in idx_to_offset_dict.items():`.
   - Compute `sanitized_idx = idx + preceding_offset`, then increment `preceding_offset += offset`.
   - Check `if error_line_start <= sanitized_idx < position:` before adding `cumulative_offset += offset`.
