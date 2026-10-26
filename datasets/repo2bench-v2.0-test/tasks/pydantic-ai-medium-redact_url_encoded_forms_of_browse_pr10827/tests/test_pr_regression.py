from pathlib import Path
import ast, json
from urllib.parse import quote_plus, urlsplit

def _load_secret_placeholders():
    p = Path("/workspace/src/pydantic_ai_harness/pydantic_ai_harness/browser_use/_toolset.py")
    if not p.is_file():
        p = Path("src/pydantic_ai_harness/pydantic_ai_harness/browser_use/_toolset.py")
    src = p.read_text(encoding="utf-8")
    tree = ast.parse(src)
    ns = {"json": json, "quote_plus": quote_plus, "urlsplit": urlsplit}
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "_secret_placeholders":
            exec(compile(ast.Module(body=[node], type_ignores=[]), str(p), "exec"), ns)
            return ns["_secret_placeholders"]
    raise AssertionError("_secret_placeholders not found")

def test_quote_plus_encoded_secret_included():
    fn = _load_secret_placeholders()
    mapping = fn({"https://safe.example": {"x_password": "p@ss word"}})
    assert mapping.get("p@ss word") == "<secret>x_password</secret>"
    assert mapping.get("p%40ss+word") == "<secret>x_password</secret>"

def test_raw_value_beats_another_secrets_encoding():
    fn = _load_secret_placeholders()
    escaped_hi = 'say ' + chr(92) + '"hi' + chr(92) + '"'
    mapping = fn({"https://safe.example": {"a": 'say "hi"', "b": escaped_hi}})
    assert mapping[escaped_hi] == "<secret>b</secret>"

def test_lone_surrogate_quote_plus_encoded():
    fn = _load_secret_placeholders()
    raw = "p@ss" + chr(0xDCFF) + "2"
    mapping = fn({"https://safe.example": {"x_password": raw}})
    assert mapping.get(quote_plus(raw, errors="surrogatepass")) == "<secret>x_password</secret>"
