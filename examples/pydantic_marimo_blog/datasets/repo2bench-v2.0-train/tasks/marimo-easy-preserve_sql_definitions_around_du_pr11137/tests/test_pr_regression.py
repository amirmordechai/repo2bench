from pathlib import Path

def _get_sql_visitor_src() -> str:
    p = Path("/workspace/marimo/_ast/sql_visitor.py")
    if not p.is_file():
        p = Path("marimo/_ast/sql_visitor.py")
    return p.read_text(encoding="utf-8")

def test_find_sql_defs_filters_duckdb_comment_tokens():
    src = _get_sql_visitor_src()
    part = src.split("def find_sql_defs(", 1)[1].split("def ", 1)[0]
    assert '"comment"' in part or "'comment'" in part
    assert "tokens" in part
