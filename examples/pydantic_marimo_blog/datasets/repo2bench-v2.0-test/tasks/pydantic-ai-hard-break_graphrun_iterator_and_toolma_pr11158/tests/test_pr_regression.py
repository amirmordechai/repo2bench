from pathlib import Path
from dataclasses import dataclass, replace

def _read(rel: str) -> str:
    p = Path("/workspace") / rel
    if not p.is_file():
        p = Path(rel)
    return p.read_text(encoding="utf-8")

def test_graph_builder_clears_iterator_instance_on_aexit():
    src = _read("pydantic_graph/pydantic_graph/graph_builder.py")
    aexit_part = src.split("async def __aexit__", 1)[1].split("async def ", 1)[0]
    assert "finally:" in aexit_part
    assert "self._iterator_instance = None" in aexit_part

def test_tool_manager_implements_and_calls_release_context():
    src = _read("pydantic_ai_slim/pydantic_ai/tool_manager.py")
    assert "def _release_context(self)" in src
    assert "self._release_context()" in src
    assert "replace(self.ctx, tool_manager=None)" in src

def test_agent_init_registers_release_context_callback():
    src = _read("pydantic_ai_slim/pydantic_ai/agent/__init__.py")
    assert "tool_manager._release_context()" in src
