from pathlib import Path
import io, sys

def _get_cli_print_src() -> str:
    p = Path("/workspace/marimo/_cli/print.py")
    if not p.is_file():
        p = Path("marimo/_cli/print.py")
    return p.read_text(encoding="utf-8")

def test_backslashreplace_used_in_echo_fallback():
    src = _get_cli_print_src()
    assert "backslashreplace" in src
    assert ".encode(" in src and ".decode(" in src
