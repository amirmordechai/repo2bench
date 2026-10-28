from pathlib import Path
import ast, html, json

def _load_build_attr():
    p = Path("/workspace/marimo/_plugins/core/web_component.py")
    if not p.is_file():
        p = Path("marimo/_plugins/core/web_component.py")
    src = p.read_text(encoding="utf-8")
    tree = ast.parse(src)
    ns = {"encode_json_str": json.dumps, "escape": html.escape, "JSONType": object}
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "_build_attr":
            exec(compile(ast.Module(body=[node], type_ignores=[]), str(p), "exec"), ns)
            return ns["_build_attr"]
    raise AssertionError("_build_attr not found")

def test_brackets_escaped_in_build_attr():
    p = Path("/workspace/marimo/_plugins/core/web_component.py")
    if not p.is_file():
        p = Path("marimo/_plugins/core/web_component.py")
    src = p.read_text(encoding="utf-8")
    assert '.replace("[", "&#91;")' in src
    assert '.replace("]", "&#93;")' in src

def test_roundtrip_unescape_preserves_markdown_links():
    fn = _load_build_attr()
    out = fn("initial-value", "C[A](C)")
    assert "[" not in out and "]" not in out
    assert "&#91;" in out and "&#93;" in out
    raw_val = out.split("='", 1)[1].rstrip("'")
    assert json.loads(html.unescape(raw_val)) == "C[A](C)"

def test_dollar_and_backslash_still_escaped():
    fn = _load_build_attr()
    out = fn("initial-value", "$100\\path[0]")
    assert "&#36;" in out and "&#92;" in out and "&#91;" in out and "&#93;" in out
