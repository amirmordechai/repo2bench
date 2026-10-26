from pathlib import Path

def _read(rel: str) -> str:
    p = Path("/workspace") / rel
    if not p.is_file():
        p = Path(rel)
    return p.read_text(encoding="utf-8")

def test_updates_captures_serving_before_uv_run():
    src = _read("src/pydantic_clai2/pydantic_clai2/cli/self_update.py")
    assert "serving:" in src and "web: WebHandoff | None = None" in src
    cmd_part = src.split("async def command(", 1)[1]
    idx_served = cmd_part.index("served = self.serving()")
    idx_run = cmd_part.index("await self.run(")
    assert idx_served < idx_run
    assert "self.web = served if self.relaunch is not None else None" in cmd_part

def test_create_shell_wires_updates_serving():
    src = _read("src/pydantic_clai2/pydantic_clai2/runtime/session_runtime.py")
    assert "updates.serving = lambda: web_serving(loader)" in src

def test_session_runtime_handoff_returns_updates_web():
    src = _read("src/pydantic_clai2/pydantic_clai2/runtime/session_runtime.py")
    handoff_part = src.split("def handoff(self)", 1)[1].split("def ", 1)[0]
    assert "return self.updates.web" in handoff_part
