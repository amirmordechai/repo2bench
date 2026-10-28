from pathlib import Path

def _read(rel: str) -> str:
    p = Path("/workspace") / rel
    if not p.is_file():
        p = Path(rel)
    return p.read_text(encoding="utf-8")

def test_session_protocol_and_impl_track_connection_generation():
    types_src = _read("marimo/_session/types.py")
    sess_src = _read("marimo/_session/session.py")
    assert "connection_generation: int" in types_src
    assert "self.connection_generation = 0" in sess_src
    assert "self.connection_generation += 1" in sess_src

def test_session_handler_captures_connection_generation():
    src = _read("marimo/_server/api/endpoints/ws/session_handler.py")
    assert "connection_generation = session.connection_generation" in src

def test_close_aborts_on_generation_mismatch():
    src = _read("marimo/_server/api/endpoints/ws/session_handler.py")
    close_part = src.split("def _close()", 1)[1].split("def ", 1)[0]
    assert "live.connection_generation != connection_generation" in close_part
    assert "live is not session" in close_part
