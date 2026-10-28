from pathlib import Path

def _get_sql_visitor_src() -> str:
    p = Path("/workspace/marimo/_ast/sql_visitor.py")
    if not p.is_file():
        p = Path("marimo/_ast/sql_visitor.py")
    return p.read_text(encoding="utf-8")

def test_is_cte_reference_defined_in_find_sql_refs():
    src = _get_sql_visitor_src()
    part = src.split("def find_sql_refs(", 1)[1]
    assert "def is_cte_reference(" in part
    assert "exp.Insert, exp.Update, exp.Delete" in part

def test_handles_recursive_and_positional_cte_scope():
    src = _get_sql_visitor_src()
    part = src.split("def is_cte_reference(", 1)[1].split("def _collect_table_refs_excluding_ctes", 1)[0]
    assert 'with_clause.args.get("recursive")' in part
    assert "cte.alias.lower() == table_name" in part

def test_build_scope_skips_dml_cte_references():
    src = _get_sql_visitor_src()
    part = src.split("def _collect_table_refs_excluding_ctes", 1)[1]
    assert "requires_table_scan" in part
    assert "is_cte_reference(" in part
