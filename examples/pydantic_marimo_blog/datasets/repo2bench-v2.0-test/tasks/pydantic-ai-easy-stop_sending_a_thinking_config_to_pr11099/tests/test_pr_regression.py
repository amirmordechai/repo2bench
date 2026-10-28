from pathlib import Path
import ast

def _load_google_profile_fn():
    src_path = Path("/workspace/pydantic_ai_slim/pydantic_ai/profiles/google.py")
    if not src_path.is_file():
        src_path = Path("pydantic_ai_slim/pydantic_ai/profiles/google.py")
    code = src_path.read_text(encoding="utf-8")
    ns = {
        "ModelProfile": dict,
        "GoogleModelProfile": dict,
        "GoogleJsonSchemaTransformer": "GoogleJsonSchemaTransformer",
        "_GOOGLE_NATIVE_TOOL_RETURN_MIME_TYPES": (),
        "_MODEL_THINKING_LEVELS": (),
    }
    tree = ast.parse(code)
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "google_model_profile":
            exec(compile(ast.Module(body=[node], type_ignores=[]), str(src_path), "exec"), ns)
    return ns["google_model_profile"]

def test_flash_image_disables_thinking():
    fn = _load_google_profile_fn()
    prof = fn("gemini-2.5-flash-image")
    assert prof["supports_thinking"] is False
    assert prof["google_supports_thinking_level"] is False

def test_flash_image_preview_disables_thinking():
    fn = _load_google_profile_fn()
    prof = fn("gemini-2.5-flash-image-preview")
    assert prof["supports_thinking"] is False
    assert prof["supports_image_output"] is True

def test_other_gemini_2_5_and_3_keep_thinking_while_flash_image_off():
    fn = _load_google_profile_fn()
    assert fn("gemini-2.5-flash-image")["supports_thinking"] is False
    p25 = fn("gemini-2.5-flash")
    assert p25["supports_thinking"] is True
    assert p25["google_supports_thinking_level"] is False
    p3 = fn("gemini-3.0-pro")
    assert p3["supports_thinking"] is True
    assert p3["google_supports_thinking_level"] is True
