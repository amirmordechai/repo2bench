# Goal: Handle multi-byte UTF-8 characters properly when `_TokenExtractor` slices SQL tokens

## Context & Goal
DuckDB's SQL tokenizer (`duckdb.tokenize`) reports token start offsets as **UTF-8 byte offsets**, not Python Unicode character indices. In `_TokenExtractor`, `self.sql_statement` is currently stored and sliced as a Python `str`. Whenever a SQL query contains multi-byte UTF-8 characters (such as accented letters, CJK characters, or emojis in comments/strings) before a `CREATE TABLE` or identifier token, `token_str(i)` slices at the wrong offset and corrupts extracted table/view names.

## Acceptance Criteria
- Store `self.sql_statement = sql_statement.encode("utf-8")` as UTF-8 `bytes` in `_TokenExtractor.__init__`, perform quote/whitespace matching in `token_str(i)` on the UTF-8 byte sequence (`b'"'`, `b"'"`, `b"e'"`, `rb"[\s\-/]"`), and `.decode("utf-8")` the returned slice.
