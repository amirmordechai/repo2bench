from pathlib import Path

def _get_google_model_src() -> str:
    p = Path("/workspace/pydantic_ai_slim/pydantic_ai/models/google.py")
    if not p.is_file():
        p = Path("pydantic_ai_slim/pydantic_ai/models/google.py")
    return p.read_text(encoding="utf-8")

def test_uses_tool_call_id_prefix_constant():
    src = _get_google_model_src()
    part = src.split("def _can_echo_server_side_tool_part(", 1)[1].split("def ", 1)[0]
    assert "_utils.TOOL_CALL_ID_PREFIX" in part or "TOOL_CALL_ID_PREFIX" in part
    assert "startswith('pyd_ai_')" not in part and 'startswith("pyd_ai_")' not in part
