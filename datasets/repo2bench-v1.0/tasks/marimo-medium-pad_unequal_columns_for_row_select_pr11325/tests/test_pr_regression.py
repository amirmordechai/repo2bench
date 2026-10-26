from pathlib import Path

def _get_default_table_src() -> str:
    p = Path("/workspace/marimo/_plugins/ui/_impl/tables/default_table.py")
    if not p.is_file():
        p = Path("marimo/_plugins/ui/_impl/tables/default_table.py")
    return p.read_text(encoding="utf-8")

def test_padded_columns_helper_defined():
    src = _get_default_table_src()
    assert "def _padded_columns(self)" in src
    assert "[None] * (num_rows - len(values))" in src

def test_select_rows_and_cells_use_padded_columns():
    src = _get_default_table_src()
    sr = src.split("def select_rows(", 1)[1].split("def ", 1)[0]
    sc = src.split("def select_cells(", 1)[1].split("def ", 1)[0]
    assert "self._padded_columns()" in sr
    assert "self._padded_columns()" in sc

def test_search_uses_padded_columns():
    src = _get_default_table_src()
    search_part = src.split("def search(", 1)[1].split("def ", 1)[0]
    assert "self._padded_columns()" in search_part
