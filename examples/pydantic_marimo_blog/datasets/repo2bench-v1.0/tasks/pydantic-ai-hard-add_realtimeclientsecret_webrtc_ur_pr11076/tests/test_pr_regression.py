from pathlib import Path
import ast

def _read(rel: str) -> str:
    p = Path("/workspace") / rel
    if not p.is_file():
        p = Path(rel)
    return p.read_text(encoding="utf-8")

def test_realtime_client_secret_has_webrtc_url_field():
    src = _read("pydantic_ai_slim/pydantic_ai/realtime/model.py")
    cls_part = src.split("class RealtimeClientSecret", 1)[1].split("class ", 1)[0]
    assert "webrtc_url: str | None = None" in cls_part

def test_mint_client_secret_accepts_and_forwards_webrtc_url():
    src = _read("pydantic_ai_slim/pydantic_ai/realtime/_openai_webrtc.py")
    fn_part = src.split("async def mint_client_secret", 1)[1]
    assert "webrtc_url: str | None" in fn_part
    assert "webrtc_url=webrtc_url" in fn_part

def test_openai_realtime_model_passes_webrtc_calls_url():
    src = _read("pydantic_ai_slim/pydantic_ai/realtime/openai.py")
    assert "webrtc_url=self._webrtc_calls_url() if self.profile.get('supports_webrtc') else None" in src or (
        "webrtc_url=" in src and "_webrtc_calls_url()" in src and "supports_webrtc" in src
    )
