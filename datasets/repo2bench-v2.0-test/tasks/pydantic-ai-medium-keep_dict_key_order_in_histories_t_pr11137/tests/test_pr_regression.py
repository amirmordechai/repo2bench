from pathlib import Path
import ast, hashlib, json, types

def _load_messages_mod():
    p = Path("/workspace/src/pydantic_ai_harness/pydantic_ai_harness/step_persistence/_messages.py")
    if not p.is_file():
        p = Path("src/pydantic_ai_harness/pydantic_ai_harness/step_persistence/_messages.py")
    src = p.read_text(encoding="utf-8")
    tree = ast.parse(src)
    ns = {"hashlib": hashlib, "json": json}
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "keyed_messages":
            exec(compile(ast.Module(body=[node], type_ignores=[]), str(p), "exec"), ns)
    mod = types.SimpleNamespace(keyed_messages=ns["keyed_messages"])
    return mod

def test_keyed_messages_preserves_top_level_dict_order():
    mod = _load_messages_mod()
    msg = {"z_key": 1, "a_key": 2, "m_key": 3}
    res = mod.keyed_messages([msg])
    assert len(res) == 1
    digest, text = res[0]
    assert text == '{"z_key":1,"a_key":2,"m_key":3}'
    assert digest == hashlib.sha256(text.encode()).hexdigest()

def test_keyed_messages_preserves_nested_tool_args_order():
    mod = _load_messages_mod()
    msg = {"part": "tool_call", "args": {"query": "shoes", "filters": {"zip": "10115", "brand": "x"}, "limit": 5}}
    _, text = mod.keyed_messages([msg])[0]
    loaded = json.loads(text)
    assert list(loaded["args"].keys()) == ["query", "filters", "limit"]
    assert list(loaded["args"]["filters"].keys()) == ["zip", "brand"]

def test_keyed_messages_distinguishes_different_key_orders():
    mod = _load_messages_mod()
    h1, t1 = mod.keyed_messages([{"b": 1, "a": 2}])[0]
    h2, t2 = mod.keyed_messages([{"a": 2, "b": 1}])[0]
    assert t1 != t2
    assert h1 != h2
