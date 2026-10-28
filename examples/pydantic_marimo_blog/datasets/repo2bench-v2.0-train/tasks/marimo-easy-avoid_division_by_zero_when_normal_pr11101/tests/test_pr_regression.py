from pathlib import Path

def _get_audio_src() -> str:
    p = Path("/workspace/marimo/_plugins/stateless/audio.py")
    if not p.is_file():
        p = Path("marimo/_plugins/stateless/audio.py")
    return p.read_text(encoding="utf-8")

def test_zero_max_abs_value_returns_one():
    src = _get_audio_src()
    part = src.split("def convert_numpy_to_wav(", 1)[1].split("def _make_audio_element(", 1)[0]
    assert "max_abs_value > 0" in part or "max_abs_value != 0" in part
