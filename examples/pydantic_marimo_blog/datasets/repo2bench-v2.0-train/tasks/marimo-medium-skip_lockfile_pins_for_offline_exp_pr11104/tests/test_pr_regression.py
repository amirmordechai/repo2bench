from pathlib import Path

def _get_export_file_src() -> str:
    p = Path("/workspace/marimo/_export/file.py")
    if not p.is_file():
        p = Path("marimo/_export/file.py")
    return p.read_text(encoding="utf-8")

def test_prepare_wasm_export_pins_only_when_offline_dir_is_none():
    src = _get_export_file_src()
    prep = src.split("async def _prepare_wasm_export(", 1)[1].split("async def ", 1)[0]
    assert "request.offline_export_dir is None" in prep
    assert "pin_pep723_dependencies_for_wasm" in prep

def test_export_wasm_delegates_pinning_to_prepare():
    src = _get_export_file_src()
    ew = src.split("async def export_wasm(", 1)[1].split("async def ", 1)[0]
    assert "pin_pep723_dependencies_for_wasm" not in ew
