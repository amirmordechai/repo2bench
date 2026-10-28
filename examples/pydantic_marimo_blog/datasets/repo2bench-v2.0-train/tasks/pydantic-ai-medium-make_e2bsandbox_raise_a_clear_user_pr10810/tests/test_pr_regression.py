from pathlib import Path

def _get_e2b_src() -> str:
    p = Path("/workspace/src/pydantic_ai_harness/pydantic_ai_harness/e2b_sandbox/_backend.py")
    if not p.is_file():
        p = Path("src/pydantic_ai_harness/pydantic_ai_harness/e2b_sandbox/_backend.py")
    return p.read_text(encoding="utf-8")

def test_require_asyncio_raises_user_error():
    src = _get_e2b_src()
    assert "E2B needs the asyncio event loop: the E2B SDK runs every request on asyncio." in src

def test_kill_sandbox_and_acquire_check_asyncio():
    src = _get_e2b_src()
    kill_part = src.split("async def kill_sandbox(", 1)[1]
    assert "_require_asyncio()" in kill_part or "running_on_asyncio()" in kill_part

def test_filesystem_operations_guarded_for_asyncio():
    src = _get_e2b_src()
    for method in ("def read_bytes(", "def write_bytes(", "def stat(", "def list_dir("):
        part = src.split(method, 1)[1].split("async def ", 1)[0]
        assert "_sandbox_for_operation()" in part or "_require_asyncio()" in part
