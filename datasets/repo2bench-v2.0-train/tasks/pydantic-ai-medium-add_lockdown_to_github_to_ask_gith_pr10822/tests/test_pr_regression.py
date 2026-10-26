from pathlib import Path

def _get_gh_src() -> str:
    p = Path("/workspace/src/pydantic_ai_harness/pydantic_ai_harness/github/_capability.py")
    if not p.is_file():
        p = Path("src/pydantic_ai_harness/pydantic_ai_harness/github/_capability.py")
    return p.read_text(encoding="utf-8")

def test_lockdown_field_added():
    src = _get_gh_src()
    assert "lockdown: bool = False" in src

def test_post_init_rejects_client_with_lockdown():
    src = _get_gh_src()
    post_part = src.split("def __post_init__", 1)[1].split("def ", 1)[0]
    assert "self.lockdown" in post_part
    assert "lockdown" in post_part

def test_lockdown_header_sent():
    src = _get_gh_src()
    assert "X-MCP-Lockdown" in src
    assert "if self.lockdown:" in src
