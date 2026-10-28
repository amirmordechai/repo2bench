# Task: Preserve `hint`, `sql_line`, and `sql_col` from engine-reported `MarimoSQLException`

## Problem Description
When a SQL engine raises a `MarimoSQLException` carrying structured error coordinates (`sql_line`, `sql_col`, `sql_statement`, `hint`):
1. In `marimo/_sql/sql.py`, `sql()` catches `e` when `is_sql_parse_error(e)` is true and re-raises `MarimoSQLException(message=str(e), sql_statement=query) from e`, dropping `e.sql_line`, `e.sql_col`, `e.hint`, and `e.sql_statement` if `e` was already a `MarimoSQLException`!
2. In `marimo/_sql/error_utils.py`, `create_sql_error_from_exception()` only checks `if isinstance(exception, MarimoSQLException) and exception.hint:`, dropping `sql_line` and `sql_col` when `exception.hint` is `None`!

## Requirements
1. In `marimo/_sql/sql.py`, inside `if is_sql_parse_error(e):`, if `isinstance(e, MarimoSQLException):`, re-raise `MarimoSQLException(message=str(e), sql_statement=e.sql_statement or query, sql_line=e.sql_line, sql_col=e.sql_col, hint=e.hint) from e`.
2. In `marimo/_sql/error_utils.py`, inside `create_sql_error_from_exception()`, preserve structured metadata whenever `isinstance(exception, MarimoSQLException)` and ANY of `exception.hint is not None`, `exception.sql_statement`, `exception.sql_line is not None`, or `exception.sql_col is not None` is truthy.
