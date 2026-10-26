from pathlib import Path
import ast

def _get_google_realtime_src() -> str:
    p = Path("/workspace/pydantic_ai_slim/pydantic_ai/realtime/google.py")
    if not p.is_file():
        p = Path("pydantic_ai_slim/pydantic_ai/realtime/google.py")
    return p.read_text(encoding="utf-8")

def test_multispeaker_deprecated_decorator():
    src = _get_google_realtime_src()
    assert "deprecated" in src
    assert "PydanticAIDeprecationWarning" in src
    assert "MultiSpeakerVoiceConfig" not in src.split("def _speech_config", 1)[1].split("def ", 1)[0]

def test_check_voice_settings_raises_on_google_multi_speaker():
    src = _get_google_realtime_src()
    assert "def _check_voice_settings" in src
    assert "'google_multi_speaker' in settings" in src
    assert "self._check_voice_settings(settings)" in src

def test_speech_config_ignores_multi_speaker():
    src = _get_google_realtime_src()
    speech_part = src.split("def _speech_config", 1)[1].split("def ", 1)[0]
    assert "multi_speaker" not in speech_part
    assert "voice_config" in speech_part
