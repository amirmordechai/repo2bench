from pathlib import Path
import ast

def _read(rel: str) -> str:
    p = Path("/workspace") / rel
    if not p.is_file():
        p = Path(rel)
    return p.read_text(encoding="utf-8")

def test_default_http_limits_defined_and_exported():
    src = _read("pydantic_ai_slim/pydantic_ai/_http.py")
    assert "DEFAULT_HTTP_LIMITS" in src
    tree = ast.parse(src)
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == "__all__":
                    elts = [e.value for e in node.value.elts if isinstance(e, ast.Constant)]
                    assert "DEFAULT_HTTP_LIMITS" in elts

def test_create_async_httpx2_client_accepts_transport():
    src = _read("pydantic_ai_slim/pydantic_ai/_http.py")
    tree = ast.parse(src)
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "create_async_httpx2_client":
            kw_names = [a.arg for a in node.args.kwonlyargs]
            assert "transport" in kw_names
            seg = ast.get_source_segment(src, node)
            assert "transport=transport" in seg
            return
    raise AssertionError("create_async_httpx2_client not found")

def test_retries_uses_default_http_limits():
    src = _read("pydantic_ai_slim/pydantic_ai/retries.py")
    assert "from ._http import DEFAULT_HTTP_LIMITS" in src or "DEFAULT_HTTP_LIMITS" in src
    assert "httpx2.HTTPTransport(limits=DEFAULT_HTTP_LIMITS)" in src
    assert "httpx2.AsyncHTTPTransport(limits=DEFAULT_HTTP_LIMITS)" in src
