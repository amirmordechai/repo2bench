from pathlib import Path

def _get_fireworks_src() -> str:
    p = Path("/workspace/pydantic_ai_slim/pydantic_ai/providers/fireworks.py")
    if not p.is_file():
        p = Path("pydantic_ai_slim/pydantic_ai/providers/fireworks.py")
    return p.read_text(encoding="utf-8")

def test_fireworks_enables_supports_json_schema_output():
    src = _get_fireworks_src()
    mp_part = src.split("def model_profile(", 1)[1].split("def ", 1)[0]
    assert "supports_json_schema_output=True" in mp_part

def test_fireworks_uses_merge_profile_with_model_profile():
    src = _get_fireworks_src()
    mp_part = src.split("def model_profile(", 1)[1].split("def ", 1)[0]
    assert "ModelProfile(supports_json_schema_output=True)" in mp_part

def test_fireworks_does_not_override_json_object_output():
    src = _get_fireworks_src()
    mp_part = src.split("def model_profile(", 1)[1].split("def ", 1)[0]
    assert "supports_json_schema_output=True" in mp_part
    assert "supports_json_object_output=True" not in mp_part
