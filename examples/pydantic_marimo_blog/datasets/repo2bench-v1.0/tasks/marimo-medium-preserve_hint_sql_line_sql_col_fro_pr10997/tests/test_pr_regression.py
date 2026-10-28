from pathlib import Path

def _read(rel: str) -> str:
    p = Path("/workspace") / rel
    if not p.is_file():
        p = Path(rel)
    return p.read_text(encoding="utf-8")

def test_error_utils_preserves_line_col_when_hint_is_none():
    src = _read("marimo/_sql/error_utils.py")
    assert "exception.sql_line is not None" in src
    assert "exception.sql_col is not None" in src

def test_sql_py_reraises_marimo_sql_exception_with_coordinates():
    src = _read("marimo/_sql/sql.py")
    part = src.split("if is_sql_parse_error(e):", 1)[1]
    assert "isinstance(e, MarimoSQLException)" in part
    assert "sql_line=e.sql_line" in part
    assert "sql_col=e.sql_col" in part
    assert "hint=e.hint" in part

def test_sql_py_preserves_sql_statement_fallback():
    src = _read("marimo/_sql/sql.py")
    part = src.split("if is_sql_parse_error(e):", 1)[1]
    assert "sql_statement=e.sql_statement or query" in part
