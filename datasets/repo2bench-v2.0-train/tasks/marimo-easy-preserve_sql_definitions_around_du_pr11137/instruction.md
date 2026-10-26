# Goal: Preserve SQL table/view definitions in `find_sql_defs` when DuckDB emits comment tokens

## Context & Goal
In DuckDB 2, `duckdb.tokenize(sql_statement)` emits SQL comments (`-- ...` or `/* ... */`) as tokens with type `duckdb.token_type.comment`. When a comment appears before or inside a `CREATE TABLE` / `CREATE VIEW` statement (or between qualified name segments like `schema./*c*/tbl`), `find_sql_defs` fails to match the `CREATE` token sequence and drops or truncates the created table/view definition.

## Acceptance Criteria
- In `find_sql_defs`, filter out comment tokens (`getattr(duckdb.token_type, "comment", None)`) from the token list returned by `duckdb.tokenize(sql_statement)` before passing `tokens` to `_TokenExtractor`, while remaining compatible with DuckDB versions that do not define `token_type.comment`.
