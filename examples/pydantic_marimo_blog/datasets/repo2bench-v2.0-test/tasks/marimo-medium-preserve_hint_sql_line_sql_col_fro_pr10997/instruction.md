# Goal: Preserve `sql_line`, `sql_col`, `hint`, and `sql_statement` when re-raising or formatting `MarimoSQLException`

## Context & Goal
When a SQL engine raises a `MarimoSQLException` that already carries structured error location fields (`sql_line`, `sql_col`, `sql_statement`, `hint`), two places accidentally strip those fields:
1. In `sql()`, when `is_sql_parse_error(e)` is true, it constructs a new `MarimoSQLException(message=str(e), sql_statement=query)` without preserving `e.sql_statement or query`, `e.sql_line`, `e.sql_col`, and `e.hint` when `isinstance(e, MarimoSQLException)`.
2. In `create_sql_error_from_exception()`, it only checks `if isinstance(exception, MarimoSQLException) and exception.hint:`, dropping `sql_line` and `sql_col` whenever `exception.hint` is `None`.

## Acceptance Criteria
1. In `sql()`, when `is_sql_parse_error(e)` and `isinstance(e, MarimoSQLException)`, re-raise `MarimoSQLException` preserving `sql_statement=e.sql_statement or query`, `sql_line=e.sql_line`, `sql_col=e.sql_col`, and `hint=e.hint`.
2. In `create_sql_error_from_exception()`, preserve structured metadata whenever `isinstance(exception, MarimoSQLException)` and any of `exception.hint is not None`, `exception.sql_statement`, `exception.sql_line is not None`, or `exception.sql_col is not None` is truthy.
