from pathlib import Path

def _read(rel: str) -> str:
    p = Path("/workspace") / rel
    if not p.is_file():
        p = Path(rel)
    return p.read_text(encoding="utf-8")

def test_global_settings_has_enable_host():
    src = _read("marimo/_config/settings.py")
    assert 'ENABLE_HOST: bool = is_env_true("MARIMO_ENABLE_HOST")' in src

def test_host_lifespan_checks_enable_host():
    src = _read("marimo/_server/host/lifespan.py")
    assert "GLOBAL_SETTINGS.ENABLE_HOST" in src
    assert "not GLOBAL_SETTINGS.ENABLE_HOST" in src

def test_create_starlette_app_gates_host_middleware():
    src = _read("marimo/_server/main.py")
    part = src.split("def create_starlette_app(", 1)[1].split("def ", 1)[0]
    assert "if GLOBAL_SETTINGS.ENABLE_HOST:" in part
    assert "HostApiMiddleware" in part
