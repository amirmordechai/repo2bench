from pathlib import Path
import ast, re
from typing import Any

def _load_token_extractor():
    p = Path("/workspace/marimo/_ast/sql_visitor.py")
    if not p.is_file():
        p = Path("marimo/_ast/sql_visitor.py")
    src = p.read_text(encoding="utf-8")
    tree = ast.parse(src)
    ns = {"Any": Any, "re": re}
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "_TokenExtractor":
            exec(compile(ast.Module(body=[node], type_ignores=[]), str(p), "exec"), ns)
            return ns["_TokenExtractor"]
    raise AssertionError("_TokenExtractor not found")

def test_utf8_byte_offsets_extracted_correctly():
    cls = _load_token_extractor()
    sql = "-- café résumé ☕\nCREATE TABLE my_tbl AS SELECT 1"
    byte_start = sql.encode("utf-8").index(b"my_tbl")
    ext = cls(sql, [(byte_start, 0)])
    assert ext.token_str(0) == "my_tbl"

def test_quoted_identifier_after_multibyte_comment():
    cls = _load_token_extractor()
    sql = "/* 日本語 */ CREATE TABLE \"quoted_tbl\" AS SELECT 1"
    byte_start = sql.encode("utf-8").index(b'"quoted_tbl"')
    ext = cls(sql, [(byte_start, 0)])
    assert ext.token_str(0) == '"quoted_tbl"'
