#!/usr/bin/env python3
"""Build and validate the 20-task `repo2bench-v1.0` Harbor benchmark dataset.

Mines 10 real October 2026 commits from `pydantic/pydantic-ai` and 10 from
`marimo-team/marimo` (stratified 7 easy / 8 medium / 5 hard), emits Harbor
task folders under `datasets/repo2bench-v1.0`,
and verifies the strict Fail-to-Pass (`nop == 0.0` -> `oracle == 1.0`) gate on all 20 tasks.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

REPO2BENCH_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO2BENCH_ROOT / "src"))

from repo2bench.git_miner import MinedCommit, mine_repository
from repo2bench.harbor_emitter import emit_harbor_task
from repo2bench.validator import validate_dataset


TASK_SPECS: dict[str, dict] = {
    # =========================================================================
    # 10 TASKS FROM pydantic/pydantic-ai (3 easy, 4 medium, 3 hard)
    # =========================================================================
    "ca7dc6c4": {
        "difficulty": "easy",
        "subset": ["pydantic_ai_slim/pydantic_ai/profiles", "tests/profiles"],
        "instruction": """# Task: Stop sending a thinking config to `gemini-2.5-flash-image`

## Problem Description
In `pydantic_ai_slim/pydantic_ai/profiles/google.py`, `google_model_profile(model_name)` currently treats all `gemini-2.5-*` models as supporting thinking (`supports_thinking=True`). However, both the Gemini API and Vertex AI reject any thinking configuration (`thinkingConfig` / `includeThoughts` / `thinkingBudget`) for `gemini-2.5-flash-image` with a 400 error (`Thinking is not enabled for this model`).

## Requirements
1. Update `google_model_profile` in `pydantic_ai_slim/pydantic_ai/profiles/google.py` so that any model name containing `'gemini-2.5-flash-image'` sets `supports_thinking = False` and `google_supports_thinking_level = False` (just like Gemma and pre-Gemini-2.5 models).
2. Ensure other Gemini 2.5 models (such as `'gemini-2.5-flash'` and `'gemini-2.5-pro'`) continue to report `supports_thinking = True` and `google_supports_thinking_level = False`, while Gemini 3+ models report both as `True`.
""",
        "regression_test": """from pathlib import Path
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
""",
    },
    "3ea7e54e": {
        "difficulty": "easy",
        "subset": ["pydantic_ai_slim/pydantic_ai/agent", "tests/test_run_reference_cycles.py"],
        "instruction": """# Task: Stop `Agent.run_stream` name inference from keeping `deps` alive until GC

## Problem Description
In `pydantic_ai_slim/pydantic_ai/agent/abstract.py`, inside `AbstractAgent.run_stream()`, when `infer_name and self.name is None` is true, `if frame := inspect.currentframe(): self._infer_name(frame.f_back)` leaves the local variable `frame` bound inside the async generator's frame. Because `frame` refers to the generator's own execution frame, it creates a reference cycle that keeps `deps` alive until garbage collection runs.

## Requirements
1. In `pydantic_ai_slim/pydantic_ai/agent/abstract.py`, inside `run_stream`'s `if infer_name and self.name is None:` block, explicitly `del frame` immediately after `if frame := inspect.currentframe(): self._infer_name(frame.f_back)`.
2. Ensure `run_stream` still calls `self._infer_name(frame.f_back)` when `frame` is not None and does not retain `frame` in local variables afterward.
""",
        "regression_test": """from pathlib import Path
import ast

def _get_run_stream_ast():
    p = Path("/workspace/pydantic_ai_slim/pydantic_ai/agent/abstract.py")
    if not p.is_file():
        p = Path("pydantic_ai_slim/pydantic_ai/agent/abstract.py")
    src = p.read_text(encoding="utf-8")
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "run_stream":
            return node, ast.get_source_segment(src, node)
    raise AssertionError("run_stream not found")

def test_run_stream_deletes_frame_local():
    node, seg = _get_run_stream_ast()
    deleted_names = [
        t.id for n in ast.walk(node) if isinstance(n, ast.Delete)
        for t in n.targets if isinstance(t, ast.Name)
    ]
    assert "frame" in deleted_names, "run_stream must `del frame` to break the frame reference cycle"

def test_run_stream_infer_name_block_intact():
    node, seg = _get_run_stream_ast()
    assert "self._infer_name(frame.f_back)" in seg
    assert "del frame" in seg

def test_frame_deleted_before_yield():
    node, seg = _get_run_stream_ast()
    idx_infer = seg.index("self._infer_name(frame.f_back)")
    idx_del = seg.index("del frame")
    idx_yield = seg.index("yield ")
    assert idx_infer < idx_del < idx_yield
""",
    },
    "d64b3453": {
        "difficulty": "easy",
        "subset": ["src/pydantic_ai_harness/pydantic_ai_harness/browser_use", "tests/harness/browser_use"],
        "instruction": """# Task: Redact URL-encoded forms of `BrowserUse` secrets in `browse_web` results

## Problem Description
In `src/pydantic_ai_harness/pydantic_ai_harness/browser_use/_toolset.py`, `_secret_placeholders(sensitive_data)` builds a dictionary mapping each secret value and its JSON-escaped form to `<secret>{key}</secret>`. However:
1. When `browser-use` blocks a search navigation, it reports the URL built with `urllib.parse.quote_plus(value, errors='surrogatepass')` (e.g. `p%40ss+word` for `p@ss word`), leaking the URL-encoded secret.
2. If secret `b`'s raw value equals secret `a`'s encoded/escaped form, iterating raw and encoded forms in a single loop causes `a`'s encoded placeholder to overwrite `b`'s raw value placeholder.

## Requirements
1. Update `_secret_placeholders` in `src/pydantic_ai_harness/pydantic_ai_harness/browser_use/_toolset.py` to:
   - First register all `<secret>{key}</secret>` self-mappings and raw `value -> placeholder` mappings across all non-empty secrets.
   - Then in a second pass register `json.dumps(value, ensure_ascii=False)[1:-1]` and `quote_plus(value, errors='surrogatepass')` via `placeholders.setdefault(...)`.
""",
        "regression_test": """from pathlib import Path
import ast, json
from urllib.parse import quote_plus, urlsplit

def _load_secret_placeholders():
    p = Path("/workspace/src/pydantic_ai_harness/pydantic_ai_harness/browser_use/_toolset.py")
    if not p.is_file():
        p = Path("src/pydantic_ai_harness/pydantic_ai_harness/browser_use/_toolset.py")
    src = p.read_text(encoding="utf-8")
    tree = ast.parse(src)
    ns = {"json": json, "quote_plus": quote_plus, "urlsplit": urlsplit}
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "_secret_placeholders":
            exec(compile(ast.Module(body=[node], type_ignores=[]), str(p), "exec"), ns)
            return ns["_secret_placeholders"]
    raise AssertionError("_secret_placeholders not found")

def test_quote_plus_encoded_secret_included():
    fn = _load_secret_placeholders()
    mapping = fn({"https://safe.example": {"x_password": "p@ss word"}})
    assert mapping.get("p@ss word") == "<secret>x_password</secret>"
    assert mapping.get("p%40ss+word") == "<secret>x_password</secret>"

def test_raw_value_beats_another_secrets_encoding():
    fn = _load_secret_placeholders()
    escaped_hi = 'say ' + chr(92) + '"hi' + chr(92) + '"'
    mapping = fn({"https://safe.example": {"a": 'say "hi"', "b": escaped_hi}})
    assert mapping[escaped_hi] == "<secret>b</secret>"

def test_lone_surrogate_quote_plus_encoded():
    fn = _load_secret_placeholders()
    raw = "p@ss" + chr(0xDCFF) + "2"
    mapping = fn({"https://safe.example": {"x_password": raw}})
    assert mapping.get(quote_plus(raw, errors="surrogatepass")) == "<secret>x_password</secret>"
""",
    },
    "218e6427": {
        "difficulty": "medium",
        "subset": ["pydantic_ai_slim/pydantic_ai/_http.py", "pydantic_ai_slim/pydantic_ai/retries.py", "tests/test_http_client_defaults.py", "tests/test_tenacity.py"],
        "instruction": """# Task: Accept `transport=` in `create_async_httpx2_client()` and use `DEFAULT_HTTP_LIMITS` in `httpx2` retry transports

## Problem Description
In `pydantic_ai_slim/pydantic_ai/_http.py` and `pydantic_ai_slim/pydantic_ai/retries.py`:
1. `create_async_httpx2_client()` does not accept a custom `transport: httpx2.AsyncBaseTransport | None = None` parameter and does not export `DEFAULT_HTTP_LIMITS` in `__all__`.
2. `HTTPX2TenacityTransport` and `AsyncHTTPX2TenacityTransport` in `pydantic_ai/retries.py` construct `httpx2.HTTPTransport()` and `httpx2.AsyncHTTPTransport()` without passing `limits=DEFAULT_HTTP_LIMITS` when `wrapped` is not provided.

## Requirements
1. In `pydantic_ai_slim/pydantic_ai/_http.py`:
   - Define `DEFAULT_HTTP_LIMITS = httpx2.Limits(max_connections=DEFAULT_MAX_CONNECTIONS, max_keepalive_connections=DEFAULT_MAX_KEEPALIVE_CONNECTIONS)` and export `'DEFAULT_HTTP_LIMITS'` in `__all__`.
   - Add `transport: httpx2.AsyncBaseTransport | None = None` (with default `limits: httpx2.Limits = DEFAULT_HTTP_LIMITS`) to `create_async_httpx2_client()` and forward `transport=transport` to `httpx2.AsyncClient(...)`.
2. In `pydantic_ai_slim/pydantic_ai/retries.py`:
   - Import `DEFAULT_HTTP_LIMITS` from `._http` and use `httpx2.HTTPTransport(limits=DEFAULT_HTTP_LIMITS)` / `httpx2.AsyncHTTPTransport(limits=DEFAULT_HTTP_LIMITS)` as the default when `wrapped` is None in `HTTPX2TenacityTransport.__init__` and `AsyncHTTPX2TenacityTransport.__init__`.
""",
        "regression_test": """from pathlib import Path
import ast

def _read(rel: str) -> str:
    p = Path("/workspace") / rel
    if not p.is_file():
        p = Path(rel)
    return p.read_text(encoding="utf-8")

def test_default_http_limits_defined_and_exported():
    src = _read("pydantic_ai_slim/pydantic_ai/_http.py")
    assert "DEFAULT_HTTP_LIMITS" in src
    tree = ast.parse(src)
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == "__all__":
                    elts = [e.value for e in node.value.elts if isinstance(e, ast.Constant)]
                    assert "DEFAULT_HTTP_LIMITS" in elts

def test_create_async_httpx2_client_accepts_transport():
    src = _read("pydantic_ai_slim/pydantic_ai/_http.py")
    tree = ast.parse(src)
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "create_async_httpx2_client":
            kw_names = [a.arg for a in node.args.kwonlyargs]
            assert "transport" in kw_names
            seg = ast.get_source_segment(src, node)
            assert "transport=transport" in seg
            return
    raise AssertionError("create_async_httpx2_client not found")

def test_retries_uses_default_http_limits():
    src = _read("pydantic_ai_slim/pydantic_ai/retries.py")
    assert "from ._http import DEFAULT_HTTP_LIMITS" in src or "DEFAULT_HTTP_LIMITS" in src
    assert "httpx2.HTTPTransport(limits=DEFAULT_HTTP_LIMITS)" in src
    assert "httpx2.AsyncHTTPTransport(limits=DEFAULT_HTTP_LIMITS)" in src
""",
    },
    "5b3ede47": {
        "difficulty": "medium",
        "subset": ["pydantic_graph/pydantic_graph", "tests/graph/builder/test_graph_edge_cases.py"],
        "instruction": """# Task: Keep `bool` and `int` inputs on separate `Literal` decision branches in `pydantic_graph`

## Problem Description
In Python, `isinstance(True, int)` is `True` and `True == 1` (`False == 0`). In `pydantic_graph/pydantic_graph/graph_builder.py`, inside `_GraphIterator` when matching a decision branch whose `branch_source` origin is `Literal`:
`inputs_match = inputs in get_args(branch_source)`
matches `inputs = 1` against `Literal[True]` and `inputs = True` against `Literal[1]`.

## Requirements
1. In `pydantic_graph/pydantic_graph/graph_builder.py`, when `get_origin(branch_source) is Literal`:
   - Extract `literal_values = get_args(branch_source)`.
   - If `isinstance(inputs, int)`, filter `literal_values` so that `int`/`bool` literal members only match when `isinstance(v, bool) == isinstance(inputs, bool)` (while non-bool `int` values like `IntEnum` members still match `int` literals).
   - Then check `inputs_match = inputs in literal_values`.
""",
        "regression_test": """from pathlib import Path
from enum import IntEnum, StrEnum
from typing import Any, Literal, get_args, get_origin

def _load_branch_matcher():
    p = Path("/workspace/pydantic_graph/pydantic_graph/graph_builder.py")
    if not p.is_file():
        p = Path("pydantic_graph/pydantic_graph/graph_builder.py")
    src = p.read_text(encoding="utf-8")
    # Extract the exactelif get_origin(branch_source) is Literal block
    lines = src.splitlines()
    block = []
    in_block = False
    indent = 0
    for ln in lines:
        if "elif get_origin(branch_source) is Literal:" in ln:
            in_block = True
            indent = len(ln) - len(ln.lstrip())
            block.append("if get_origin(branch_source) is Literal:")
            continue
        if in_block:
            cur_indent = len(ln) - len(ln.lstrip()) if ln.strip() else indent + 4
            if ln.strip() and cur_indent <= indent:
                break
            block.append(ln[indent:])
    code = "\\n".join(block)
    def match(inputs, branch_source):
        ns = {"inputs": inputs, "branch_source": branch_source, "Literal": Literal, "get_origin": get_origin, "get_args": get_args}
        exec(code, ns)
        return ns["inputs_match"]
    return match

def test_bool_does_not_match_int_literal():
    match = _load_branch_matcher()
    assert match(True, Literal[1]) is False
    assert match(False, Literal[0]) is False
    assert match(True, Literal[True]) is True

def test_int_does_not_match_bool_literal():
    match = _load_branch_matcher()
    assert match(1, Literal[True]) is False
    assert match(0, Literal[False]) is False
    assert match(1, Literal[1]) is True

def test_enums_still_match_literals():
    class Level(IntEnum):
        HIGH = 1
    match = _load_branch_matcher()
    assert match(Level.HIGH, Literal[True]) is False
    assert match(Level.HIGH, Literal[1]) is True
""",
    },
    "21162072": {
        "difficulty": "medium",
        "subset": ["pydantic_ai_slim/pydantic_ai/realtime/google.py", "tests/realtime/test_google.py"],
        "instruction": """# Task: Deprecate `google_multi_speaker` on `GoogleRealtimeModel` and reject it before dialing

## Problem Description
No Gemini Live model supports multi-speaker voice configurations (`multi_speaker_voice_config`). In `pydantic_ai_slim/pydantic_ai/realtime/google.py`, `GoogleRealtimeModel` currently builds `MultiSpeakerVoiceConfig` in `_speech_config()` and does not reject `google_multi_speaker` before opening a WebSocket session.

## Requirements
1. In `pydantic_ai_slim/pydantic_ai/realtime/google.py`:
   - Decorate `MultiSpeaker` with `@deprecated(..., category=PydanticAIDeprecationWarning)` (importing `deprecated` from `typing_extensions`).
   - Simplify `_speech_config(self, model_settings: GoogleRealtimeModelSettings)` so it only builds `voice_config` from `google_voice` and `language_code` from `google_language_code` (returning `None` when both are absent, and no longer constructing `MultiSpeakerVoiceConfig`).
   - Add a `_check_voice_settings(self, settings: GoogleRealtimeModelSettings) -> None` method on `GoogleRealtimeModel` that raises `UserError` (`'`google_multi_speaker` is deprecated and not supported by any Gemini Live model...'`) if `'google_multi_speaker' in settings`, and also checks `google_affective_dialog`, calling `self._check_voice_settings(settings)` before dialing.
""",
        "regression_test": """from pathlib import Path
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
""",
    },
    "bfe3f6d6": {
        "difficulty": "medium",
        "subset": ["src/pydantic_ai_harness/pydantic_ai_harness/step_persistence", "tests/harness/step_persistence"],
        "instruction": """# Task: Keep dict key order in histories that step stores reload (`keyed_messages`)

## Problem Description
In `src/pydantic_ai_harness/pydantic_ai_harness/step_persistence/_messages.py`, `keyed_messages(messages)` currently serializes each message with:
`text = json.dumps(message, sort_keys=True, separators=(',', ':'))`
Sorting dictionary keys alters the key order of tool call arguments, tool return payloads, and `provider_details` when a snapshot is reloaded from step persistence, invalidating downstream provider prompt caches on resumed runs.

## Requirements
1. In `src/pydantic_ai_harness/pydantic_ai_harness/step_persistence/_messages.py`, remove `sort_keys=True` from `json.dumps(message, separators=(',', ':'))` inside `keyed_messages(messages)` so original dictionary key insertion order is preserved in both the stored JSON text and its SHA-256 hash.
""",
        "regression_test": """from pathlib import Path
import ast, hashlib, json, types

def _load_messages_mod():
    p = Path("/workspace/src/pydantic_ai_harness/pydantic_ai_harness/step_persistence/_messages.py")
    if not p.is_file():
        p = Path("src/pydantic_ai_harness/pydantic_ai_harness/step_persistence/_messages.py")
    src = p.read_text(encoding="utf-8")
    tree = ast.parse(src)
    ns = {"hashlib": hashlib, "json": json}
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "keyed_messages":
            exec(compile(ast.Module(body=[node], type_ignores=[]), str(p), "exec"), ns)
    mod = types.SimpleNamespace(keyed_messages=ns["keyed_messages"])
    return mod

def test_keyed_messages_preserves_top_level_dict_order():
    mod = _load_messages_mod()
    msg = {"z_key": 1, "a_key": 2, "m_key": 3}
    res = mod.keyed_messages([msg])
    assert len(res) == 1
    digest, text = res[0]
    assert text == '{"z_key":1,"a_key":2,"m_key":3}'
    assert digest == hashlib.sha256(text.encode()).hexdigest()

def test_keyed_messages_preserves_nested_tool_args_order():
    mod = _load_messages_mod()
    msg = {"part": "tool_call", "args": {"query": "shoes", "filters": {"zip": "10115", "brand": "x"}, "limit": 5}}
    _, text = mod.keyed_messages([msg])[0]
    loaded = json.loads(text)
    assert list(loaded["args"].keys()) == ["query", "filters", "limit"]
    assert list(loaded["args"]["filters"].keys()) == ["zip", "brand"]

def test_keyed_messages_distinguishes_different_key_orders():
    mod = _load_messages_mod()
    h1, t1 = mod.keyed_messages([{"b": 1, "a": 2}])[0]
    h2, t2 = mod.keyed_messages([{"a": 2, "b": 1}])[0]
    assert t1 != t2
    assert h1 != h2
""",
    },
    "e5d08153": {
        "difficulty": "hard",
        "subset": ["pydantic_ai_slim/pydantic_ai/agent/__init__.py", "pydantic_ai_slim/pydantic_ai/tool_manager.py", "pydantic_graph/pydantic_graph/graph_builder.py", "tests/graph/builder"],
        "instruction": """# Task: Break `GraphRun` iterator and `ToolManager` context reference cycles

## Problem Description
Completed `Agent.run` and `GraphBuilder` runs retain `deps` in reference cycles until garbage collection runs because:
1. In `pydantic_graph/pydantic_graph/graph_builder.py`, `GraphRun._iterator_instance` holds bound callbacks referring back to `GraphRun`; `__aexit__` does not clear `self._iterator_instance = None` in a `finally:` block.
2. In `pydantic_ai_slim/pydantic_ai/tool_manager.py`, `ToolManager.ctx` refers to a `RunContext` whose `.tool_manager` refers back to `self`. `ToolManager` needs a `_release_context(self) -> None` method (`if self.ctx is not None and self.ctx.tool_manager is self: self.ctx = replace(self.ctx, tool_manager=None)`) called at the end of `for_run_step` and registered via `stack.callback(lambda: graph_deps.tool_manager._release_context())` in `_PreparedAgentRun` in `pydantic_ai_slim/pydantic_ai/agent/__init__.py`.

## Requirements
1. In `pydantic_graph/pydantic_graph/graph_builder.py`, ensure `GraphRun.__aexit__` sets `self._iterator_instance = None` in a `try ... finally:` block after awaiting `self._async_exit_stack.__aexit__(...)`, and assert `self._iterator_instance is not None` in `_iterator_context`.
2. In `pydantic_ai_slim/pydantic_ai/tool_manager.py`, implement `_release_context(self) -> None` on `ToolManager` and call `self._release_context()` in `for_run_step` before returning `new_tm`.
3. In `pydantic_ai_slim/pydantic_ai/agent/__init__.py`, register `stack.callback(lambda: graph_deps.tool_manager._release_context())` on the `AsyncExitStack` in `_PreparedAgentRun`.
""",
        "regression_test": """from pathlib import Path
from dataclasses import dataclass, replace

def _read(rel: str) -> str:
    p = Path("/workspace") / rel
    if not p.is_file():
        p = Path(rel)
    return p.read_text(encoding="utf-8")

def test_graph_builder_clears_iterator_instance_on_aexit():
    src = _read("pydantic_graph/pydantic_graph/graph_builder.py")
    aexit_part = src.split("async def __aexit__", 1)[1].split("async def ", 1)[0]
    assert "finally:" in aexit_part
    assert "self._iterator_instance = None" in aexit_part

def test_tool_manager_implements_and_calls_release_context():
    src = _read("pydantic_ai_slim/pydantic_ai/tool_manager.py")
    assert "def _release_context(self)" in src
    assert "self._release_context()" in src
    assert "replace(self.ctx, tool_manager=None)" in src

def test_agent_init_registers_release_context_callback():
    src = _read("pydantic_ai_slim/pydantic_ai/agent/__init__.py")
    assert "tool_manager._release_context()" in src
""",
    },
    "3e3a6214": {
        "difficulty": "hard",
        "subset": ["pydantic_ai_slim/pydantic_ai/realtime", "tests/realtime"],
        "instruction": """# Task: Add `RealtimeClientSecret.webrtc_url` for OpenAI and Azure OpenAI WebRTC calls

## Problem Description
When a browser uses an ephemeral `RealtimeClientSecret` token minted by `OpenAIRealtimeModel`, it needs to know the URL where it should POST its WebRTC SDP offer (which on Azure OpenAI includes `?webrtcfilter=on`, and on providers without WebRTC support is `None`).

## Requirements
1. In `pydantic_ai_slim/pydantic_ai/realtime/model.py`, add `webrtc_url: str | None = None` to the `RealtimeClientSecret` dataclass (after `expires_at`).
2. In `pydantic_ai_slim/pydantic_ai/realtime/_openai_webrtc.py`, add `webrtc_url: str | None` to `mint_client_secret(...)` and pass `webrtc_url=webrtc_url` when constructing `RealtimeClientSecret`.
3. In `pydantic_ai_slim/pydantic_ai/realtime/openai.py`, pass `webrtc_url=self._webrtc_calls_url() if self.profile.get('supports_webrtc') else None` to `mint_client_secret(...)`.
""",
        "regression_test": """from pathlib import Path
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
""",
    },
    "5a09a0c8": {
        "difficulty": "hard",
        "subset": ["src/pydantic_clai2/pydantic_clai2", "tests/clai2"],
        "instruction": """# Task: Stop `clai2` from crashing with `ImportError` when it restarts after `/update`

## Problem Description
When `/update` runs `uv` to upgrade `clai2` in-place while a session is running, calling `web_serving(self.loader)` *after* `uv` has replaced the installed files on disk can trigger a lazy import of a newly upgraded module whose symbols conflict with the old in-memory modules, crashing with `ImportError`.

## Requirements
1. In `src/pydantic_clai2/pydantic_clai2/cli/self_update.py`:
   - Add `serving: Callable[[], WebHandoff | None] = lambda: None` and `web: WebHandoff | None = None` fields to `Updates`.
   - Inside `Updates.command()`, call `served = self.serving()` *before* running `uv` (`with CancelScope(shield=True):`), and after `self.relaunch = await self.locate(uv)` set `self.web = served if self.relaunch is not None else None`.
2. In `src/pydantic_clai2/pydantic_clai2/runtime/session_runtime.py`:
   - Wire `updates.serving = lambda: web_serving(loader)` in `create_shell`.
   - Update `SessionRuntime.handoff(self)` to return `self.updates.web`.
""",
        "regression_test": """from pathlib import Path

def _read(rel: str) -> str:
    p = Path("/workspace") / rel
    if not p.is_file():
        p = Path(rel)
    return p.read_text(encoding="utf-8")

def test_updates_captures_serving_before_uv_run():
    src = _read("src/pydantic_clai2/pydantic_clai2/cli/self_update.py")
    assert "serving:" in src and "web: WebHandoff | None = None" in src
    cmd_part = src.split("async def command(", 1)[1]
    idx_served = cmd_part.index("served = self.serving()")
    idx_run = cmd_part.index("await self.run(")
    assert idx_served < idx_run
    assert "self.web = served if self.relaunch is not None else None" in cmd_part

def test_create_shell_wires_updates_serving():
    src = _read("src/pydantic_clai2/pydantic_clai2/runtime/session_runtime.py")
    assert "updates.serving = lambda: web_serving(loader)" in src

def test_session_runtime_handoff_returns_updates_web():
    src = _read("src/pydantic_clai2/pydantic_clai2/runtime/session_runtime.py")
    handoff_part = src.split("def handoff(self)", 1)[1].split("def ", 1)[0]
    assert "return self.updates.web" in handoff_part
""",
    },
    # =========================================================================
    # 10 TASKS FROM marimo-team/marimo (4 easy, 4 medium, 2 hard)
    # =========================================================================
    "774844f9": {
        "difficulty": "easy",
        "subset": ["marimo/_utils/url.py", "tests/_utils/test_url.py"],
        "instruction": """# Task: Accept single-digit ports in `is_url`

## Problem Description
In `marimo/_utils/url.py`, the URL validation regular expression matches port numbers using `(?::\\d{2,5})?`, which requires at least 2 digits and rejects valid URLs with single-digit ports such as `http://127.0.0.1:8/macros.tex`.

## Requirements
1. Update the port number group in `regex` in `marimo/_utils/url.py` from `(?::\\d{2,5})?` to `(?::\\d{1,5})?` so ports from 1 to 5 digits are accepted.
""",
        "regression_test": """from pathlib import Path
import importlib.util

def _load_is_url():
    p = Path("/workspace/marimo/_utils/url.py")
    if not p.is_file():
        p = Path("marimo/_utils/url.py")
    spec = importlib.util.spec_from_file_location("url_mod", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.is_url

def test_single_digit_port_accepted():
    is_url = _load_is_url()
    assert is_url("http://127.0.0.1:8/macros.tex") is True
    assert is_url("http://localhost:9/test") is True

def test_multi_digit_and_single_digit_ports_accepted():
    is_url = _load_is_url()
    assert is_url("https://example.com:1/api") is True
    assert is_url("http://127.0.0.1:80/macros.tex") is True
    assert is_url("http://127.0.0.1:8000/macros.tex") is True
    assert is_url("http://127.0.0.1:65535/macros.tex") is True

def test_non_urls_rejected_while_single_digit_port_valid():
    is_url = _load_is_url()
    assert is_url("http://127.0.0.1:5/") is True
    assert is_url("not_a_url") is False
    assert is_url("http://127.0.0.1:123456/too_long") is False
""",
    },
    "c716635c": {
        "difficulty": "easy",
        "subset": ["marimo/_plugins/core/web_component.py", "tests/_plugins/core/test_web_component.py"],
        "instruction": """# Task: Preserve bracketed widget values in Markdown (`_build_attr`)

## Problem Description
In `marimo/_plugins/core/web_component.py`, `_build_attr(name: str, value: JSONType) -> str` escapes `\\` (`&#92;`) and `$` (`&#36;`) so widget attributes embedded inside Markdown are not corrupted by Markdown or LaTeX parsers. However, unescaped `[` and `]` inside attribute values (such as `"C[A](C)"` or `"[a][b]"`) are interpreted by the Markdown parser as Markdown links or reference links, corrupting the widget's `data-initial-value`.

## Requirements
1. Update `_build_attr` in `marimo/_plugins/core/web_component.py` to also replace `"[", "&#91;"` and `"]", "&#93;"` on `processed` before returning `f"data-{name}='{processed}'"`.
""",
        "regression_test": """from pathlib import Path
import ast, html, json

def _load_build_attr():
    p = Path("/workspace/marimo/_plugins/core/web_component.py")
    if not p.is_file():
        p = Path("marimo/_plugins/core/web_component.py")
    src = p.read_text(encoding="utf-8")
    tree = ast.parse(src)
    ns = {"encode_json_str": json.dumps, "escape": html.escape, "JSONType": object}
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "_build_attr":
            exec(compile(ast.Module(body=[node], type_ignores=[]), str(p), "exec"), ns)
            return ns["_build_attr"]
    raise AssertionError("_build_attr not found")

def test_brackets_escaped_in_build_attr():
    p = Path("/workspace/marimo/_plugins/core/web_component.py")
    if not p.is_file():
        p = Path("marimo/_plugins/core/web_component.py")
    src = p.read_text(encoding="utf-8")
    assert '.replace("[", "&#91;")' in src
    assert '.replace("]", "&#93;")' in src

def test_roundtrip_unescape_preserves_markdown_links():
    fn = _load_build_attr()
    out = fn("initial-value", "C[A](C)")
    assert "[" not in out and "]" not in out
    assert "&#91;" in out and "&#93;" in out
    raw_val = out.split("='", 1)[1].rstrip("'")
    assert json.loads(html.unescape(raw_val)) == "C[A](C)"

def test_dollar_and_backslash_still_escaped():
    fn = _load_build_attr()
    out = fn("initial-value", "$100\\\\path[0]")
    assert "&#36;" in out and "&#92;" in out and "&#91;" in out and "&#93;" in out
""",
    },
    "5e8e83e4": {
        "difficulty": "easy",
        "subset": ["marimo/_utils/docs.py", "tests/_utils/test_docs.py"],
        "instruction": """# Task: Preserve underscores in docstring code spans (`MarkdownConverter`)

## Problem Description
In `marimo/_utils/docs.py`, when `pylsp_markdown` converts docstrings that are plain Markdown containing inline backtick code spans (e.g. ``Use `shout_factor` or `a_b` ``) without structured RST/NumPy/Google sections, upstream converters escape underscores inside backtick spans.

## Requirements
1. In `marimo/_utils/docs.py`, add a `MarkdownConverter` class right after `MarimoConverter` with:
   - `priority = 0`
   - `can_convert(self, docstring: str) -> bool`: returns `True` when `re.search(r"(?<![\\\\`])(`+)(?!`)(.+?)(?<!`)\\1(?!`)", docstring, flags=re.DOTALL) is not None`
   - `convert(self, docstring: str) -> str`: returns `docstring` verbatim.
""",
        "regression_test": """from pathlib import Path
import ast, re

def _load_markdown_converter():
    p = Path("/workspace/marimo/_utils/docs.py")
    if not p.is_file():
        p = Path("marimo/_utils/docs.py")
    src = p.read_text(encoding="utf-8")
    tree = ast.parse(src)
    ns = {"re": re}
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "MarkdownConverter":
            exec(compile(ast.Module(body=[node], type_ignores=[]), str(p), "exec"), ns)
            return ns["MarkdownConverter"], src
    raise AssertionError("MarkdownConverter class not found in marimo/_utils/docs.py")

def test_markdown_converter_matches_backtick_spans():
    cls, _ = _load_markdown_converter()
    conv = cls()
    assert conv.priority == 0
    assert conv.can_convert("Note: `shout_factor` supports all natural numbers.") is True
    assert conv.can_convert("Use ``a`b_c`` to include a backtick.") is True
    assert conv.convert("Use `a_b`.") == "Use `a_b`."

def test_markdown_converter_rejects_escaped_or_unclosed_backticks():
    cls, _ = _load_markdown_converter()
    conv = cls()
    assert conv.can_convert("Plain text without code spans.") is False
    assert conv.can_convert("Unclosed `shout_factor.") is False
    assert conv.can_convert("Escaped " + chr(92) + "`shout_factor" + chr(92) + "`.") is False

def test_markdown_converter_priority_and_multiline_code_span():
    cls, _ = _load_markdown_converter()
    conv = cls()
    assert conv.priority == 0
    assert conv.can_convert("Multiline:\\n`first_part\\nsecond_part`") is True
""",
    },
    "c15169de": {
        "difficulty": "easy",
        "subset": ["marimo/_sql/parse.py", "tests/_sql/test_sql_parse.py"],
        "instruction": """# Task: Align SQL interpolation error offsets in `_parse_sql_duckdb`

## Problem Description
In `marimo/_sql/parse.py`, inside `_parse_sql_duckdb`, `idx_to_offset_dict` maps bracket replacement indices `idx` in the *original* SQL string to the length `offset` of added quotes in the *sanitized* SQL string. However, DuckDB's `position` and `error_line_start` are in the *sanitized* SQL coordinate system! Comparing `error_line_start <= idx < position` directly against the unadjusted `idx` miscalculates `column_number` whenever multiple `{...}` interpolations appear before the error.

## Requirements
1. In `marimo/_sql/parse.py`, inside `_parse_sql_duckdb`:
   - Track `preceding_offset = 0` while iterating `for idx, offset in idx_to_offset_dict.items():`.
   - Compute `sanitized_idx = idx + preceding_offset`, then increment `preceding_offset += offset`.
   - Check `if error_line_start <= sanitized_idx < position:` before adding `cumulative_offset += offset`.
""",
        "regression_test": """from pathlib import Path

def _load_offset_calc():
    p = Path("/workspace/marimo/_sql/parse.py")
    if not p.is_file():
        p = Path("marimo/_sql/parse.py")
    src = p.read_text(encoding="utf-8")
    assert "sanitized_idx" in src and "preceding_offset" in src, "Must compute sanitized_idx = idx + preceding_offset"
    return src

def test_sanitized_idx_used_in_parse_sql_duckdb():
    src = _load_offset_calc()
    assert "sanitized_idx = idx + preceding_offset" in src
    assert "preceding_offset += offset" in src
    assert "error_line_start <= sanitized_idx < position" in src

def test_multiple_interpolations_on_previous_line_offset():
    _load_offset_calc()
    # Verify coordinate math with preceding replacements before newline
    # Query: "SELECT {a}, {b}, {c}, {d}, {e};\\nSELECT {value} FRM users"
    idx_to_offset_dict = {7: 2, 12: 2, 17: 2, 22: 2, 27: 2, 39: 2}
    error_line_start = 42  # sanitized newline + 1
    position = 59          # sanitized FRM position
    cumulative_offset = 0
    preceding_offset = 0
    for idx, offset in idx_to_offset_dict.items():
        sanitized_idx = idx + preceding_offset
        preceding_offset += offset
        if error_line_start <= sanitized_idx < position:
            cumulative_offset += offset
    assert cumulative_offset == 2

def test_multiple_interpolations_on_same_line_offset():
    _load_offset_calc()
    idx_to_offset_dict = {7: 2, 12: 2, 17: 2, 22: 2, 27: 2, 43: 2}
    error_line_start = 0
    position = 43
    cumulative_offset = 0
    preceding_offset = 0
    for idx, offset in idx_to_offset_dict.items():
        sanitized_idx = idx + preceding_offset
        preceding_offset += offset
        if error_line_start <= sanitized_idx < position:
            cumulative_offset += offset
    assert cumulative_offset == 10
""",
    },
    "ca983d9b": {
        "difficulty": "medium",
        "subset": ["marimo/_save/loaders/lazy.py", "tests/_save/loaders/test_loader.py"],
        "instruction": """# Task: Fall back to pickle when a typed serializer rejects a value in `LazyLoader`

## Problem Description
In `marimo/_save/loaders/lazy.py`, inside `LazyLoader.save_cache`, `_put_or_mark_unserializable` takes a single `serialize: Callable[[Any], bytes]` function and immediately marks a variable as unserializable if its typed serializer (such as Arrow/Parquet for a mixed-dtype Pandas column) raises an exception, instead of falling back to `pickle.dumps`.

## Requirements
1. In `marimo/_save/loaders/lazy.py`, change `_put_or_mark_unserializable`'s third parameter from `serialize: Callable[[Any], bytes]` to `loader: str`.
2. Inside `_put_or_mark_unserializable`, try `serializers = {loader: BLOB_SERIALIZERS.get(loader, pickle.dumps), "pickle": pickle.dumps}` in order. If a fallback `suffix != loader` succeeds, update `key = Path(key).with_suffix(f".{suffix}").as_posix()` and update `item.reference = key` for `item in items` before storing `store.put(key, data)`.
3. Update the callers of `_put_or_mark_unserializable` in `LazyLoader` to pass `return_loader`, `"pickle"`, and `loader` instead of pre-resolved `serialize` callables.
""",
        "regression_test": """from pathlib import Path

def _get_lazy_src() -> str:
    p = Path("/workspace/marimo/_save/loaders/lazy.py")
    if not p.is_file():
        p = Path("marimo/_save/loaders/lazy.py")
    return p.read_text(encoding="utf-8")

def test_put_or_mark_unserializable_accepts_loader_name():
    src = _get_lazy_src()
    fn_part = src.split("def _put_or_mark_unserializable(", 1)[1].split("def ", 1)[0]
    assert "loader: str" in fn_part
    assert '"pickle": pickle.dumps' in fn_part

def test_fallback_updates_key_suffix_and_item_references():
    src = _get_lazy_src()
    fn_part = src.split("def _put_or_mark_unserializable(", 1)[1].split("def ", 1)[0]
    assert '.with_suffix(f".{suffix}").as_posix()' in fn_part
    assert "item.reference = key" in fn_part

def test_callers_pass_loader_strings():
    src = _get_lazy_src()
    after = src.split("def _put_or_mark_unserializable(", 1)[1]
    assert "return_loader," in after
    assert '"pickle",' in after
""",
    },
    "d0b73b93": {
        "difficulty": "medium",
        "subset": ["marimo/_ast/sql_visitor.py", "tests/_ast/test_sql_visitor.py"],
        "instruction": """# Task: Exclude DML CTE aliases from SQL dependencies in `find_sql_refs`

## Problem Description
In `marimo/_ast/sql_visitor.py`, `find_sql_refs(sql_statement)` misidentifies CTE aliases in DML queries (e.g., `WITH changed AS (INSERT INTO items VALUES (1) RETURNING *) SELECT * FROM changed`) or nested subquery CTEs as external table dependencies because:
1. `build_scope(expression)` exposes DML CTE references as plain `exp.Table` sources.
2. `_collect_table_refs_excluding_ctes` only checks top-level `WITH` clauses and fails to distinguish the target table of an `INSERT`/`UPDATE`/`DELETE` from a CTE reference of the same name, or recursive vs non-recursive CTE self-references.

## Requirements
1. In `marimo/_ast/sql_visitor.py`, inside `find_sql_refs`, implement `is_cte_reference(table: exp.Table) -> bool` that:
   - Returns `False` if `table.db or table.catalog`, or if `table` (or its parent `exp.Schema`) is the direct target (`parent.this is target`) of an `exp.Insert`, `exp.Update`, or `exp.Delete`.
   - Walks ancestor `parent` nodes checking `with_clause` (`parent` if `isinstance(parent, exp.With)` else `parent.args.get("with_")`), and for `cte in with_clause.expressions`: if `cte is node and not with_clause.args.get("recursive")` breaks (since non-recursive CTEs cannot reference themselves or later CTEs), if `cte.alias.lower() == table_name` returns `True`, and if `cte is node` breaks.
2. Use `not is_cte_reference(table)` in `_collect_table_refs_excluding_ctes` AND skip `source` in the `build_scope` traversal when `requires_table_scan and is_cte_reference(source)`.
""",
        "regression_test": """from pathlib import Path

def _get_sql_visitor_src() -> str:
    p = Path("/workspace/marimo/_ast/sql_visitor.py")
    if not p.is_file():
        p = Path("marimo/_ast/sql_visitor.py")
    return p.read_text(encoding="utf-8")

def test_is_cte_reference_defined_in_find_sql_refs():
    src = _get_sql_visitor_src()
    part = src.split("def find_sql_refs(", 1)[1]
    assert "def is_cte_reference(" in part
    assert "exp.Insert, exp.Update, exp.Delete" in part

def test_handles_recursive_and_positional_cte_scope():
    src = _get_sql_visitor_src()
    part = src.split("def is_cte_reference(", 1)[1].split("def _collect_table_refs_excluding_ctes", 1)[0]
    assert 'with_clause.args.get("recursive")' in part
    assert "cte.alias.lower() == table_name" in part

def test_build_scope_skips_dml_cte_references():
    src = _get_sql_visitor_src()
    part = src.split("def _collect_table_refs_excluding_ctes", 1)[1]
    assert "requires_table_scan" in part
    assert "is_cte_reference(" in part
""",
    },
    "330ca411": {
        "difficulty": "medium",
        "subset": ["marimo/_sql/error_utils.py", "marimo/_sql/sql.py", "tests/_sql/test_sql_error_handling.py"],
        "instruction": """# Task: Preserve `hint`, `sql_line`, and `sql_col` from engine-reported `MarimoSQLException`

## Problem Description
When a SQL engine raises a `MarimoSQLException` carrying structured error coordinates (`sql_line`, `sql_col`, `sql_statement`, `hint`):
1. In `marimo/_sql/sql.py`, `sql()` catches `e` when `is_sql_parse_error(e)` is true and re-raises `MarimoSQLException(message=str(e), sql_statement=query) from e`, dropping `e.sql_line`, `e.sql_col`, `e.hint`, and `e.sql_statement` if `e` was already a `MarimoSQLException`!
2. In `marimo/_sql/error_utils.py`, `create_sql_error_from_exception()` only checks `if isinstance(exception, MarimoSQLException) and exception.hint:`, dropping `sql_line` and `sql_col` when `exception.hint` is `None`!

## Requirements
1. In `marimo/_sql/sql.py`, inside `if is_sql_parse_error(e):`, if `isinstance(e, MarimoSQLException):`, re-raise `MarimoSQLException(message=str(e), sql_statement=e.sql_statement or query, sql_line=e.sql_line, sql_col=e.sql_col, hint=e.hint) from e`.
2. In `marimo/_sql/error_utils.py`, inside `create_sql_error_from_exception()`, preserve structured metadata whenever `isinstance(exception, MarimoSQLException)` and ANY of `exception.hint is not None`, `exception.sql_statement`, `exception.sql_line is not None`, or `exception.sql_col is not None` is truthy.
""",
        "regression_test": """from pathlib import Path

def _read(rel: str) -> str:
    p = Path("/workspace") / rel
    if not p.is_file():
        p = Path(rel)
    return p.read_text(encoding="utf-8")

def test_error_utils_preserves_line_col_when_hint_is_none():
    src = _read("marimo/_sql/error_utils.py")
    assert "exception.sql_line is not None" in src
    assert "exception.sql_col is not None" in src

def test_sql_py_reraises_marimo_sql_exception_with_coordinates():
    src = _read("marimo/_sql/sql.py")
    part = src.split("if is_sql_parse_error(e):", 1)[1]
    assert "isinstance(e, MarimoSQLException)" in part
    assert "sql_line=e.sql_line" in part
    assert "sql_col=e.sql_col" in part
    assert "hint=e.hint" in part

def test_sql_py_preserves_sql_statement_fallback():
    src = _read("marimo/_sql/sql.py")
    part = src.split("if is_sql_parse_error(e):", 1)[1]
    assert "sql_statement=e.sql_statement or query" in part
""",
    },
    "169d793c": {
        "difficulty": "medium",
        "subset": ["marimo/_plugins/ui/_impl/tables/default_table.py", "tests/_plugins/ui/_impl/tables/test_default_table.py"],
        "instruction": """# Task: Pad unequal columns with `None` for row selection, cell selection, and search in `DefaultTableManager`

## Problem Description
In `marimo/_plugins/ui/_impl/tables/default_table.py`, when `DefaultTableManager` holds column-oriented dictionary data where columns have different lengths (e.g. `{"a": [2], "b": [10, 20]}`), `sort_values` pads shorter columns with `None` up to `self.get_num_rows()`, but `select_rows`, `select_cells`, and `search` index directly into `self.data[key][row]`, raising `IndexError: list index out of range`!

## Requirements
1. Add a helper method `_padded_columns(self) -> dict[str, Sequence[Any]]` on `DefaultTableManager` in `marimo/_plugins/ui/_impl/tables/default_table.py` that pads any column shorter than `self.get_num_rows()` with `None` (`list(values) + [None] * (num_rows - len(values))`).
2. Use `self._padded_columns()` in `select_rows`, `select_cells`, `search`, and `sort_values` when `self.is_column_oriented` is true so shorter columns are padded with `None` without mutating `self.data`.
""",
        "regression_test": """from pathlib import Path

def _get_default_table_src() -> str:
    p = Path("/workspace/marimo/_plugins/ui/_impl/tables/default_table.py")
    if not p.is_file():
        p = Path("marimo/_plugins/ui/_impl/tables/default_table.py")
    return p.read_text(encoding="utf-8")

def test_padded_columns_helper_defined():
    src = _get_default_table_src()
    assert "def _padded_columns(self)" in src
    assert "[None] * (num_rows - len(values))" in src

def test_select_rows_and_cells_use_padded_columns():
    src = _get_default_table_src()
    sr = src.split("def select_rows(", 1)[1].split("def ", 1)[0]
    sc = src.split("def select_cells(", 1)[1].split("def ", 1)[0]
    assert "self._padded_columns()" in sr
    assert "self._padded_columns()" in sc

def test_search_uses_padded_columns():
    src = _get_default_table_src()
    search_part = src.split("def search(", 1)[1].split("def ", 1)[0]
    assert "self._padded_columns()" in search_part
""",
    },
    "c6226418": {
        "difficulty": "hard",
        "subset": ["marimo/_config/settings.py", "marimo/_server/host/lifespan.py", "marimo/_server/main.py", "tests/_server/host/test_host_record.py"],
        "instruction": """# Task: Gate host integration behind `MARIMO_ENABLE_HOST`

## Problem Description
The experimental host API and lifespan integration in Marimo currently runs unconditionally in `EDIT` mode and attaches `HostApiMiddleware` to every Starlette app. It needs to be gated behind an opt-in `MARIMO_ENABLE_HOST` environment setting (`GLOBAL_SETTINGS.ENABLE_HOST`).

## Requirements
1. In `marimo/_config/settings.py`, add `ENABLE_HOST: bool = is_env_true("MARIMO_ENABLE_HOST")` to `GlobalSettings`.
2. In `marimo/_server/host/lifespan.py`, import `GLOBAL_SETTINGS` from `marimo._config.settings` and early-return (`yield; return`) in `async def host(app: Starlette)` when `not GLOBAL_SETTINGS.ENABLE_HOST or state.mode is not SessionMode.EDIT`.
3. In `marimo/_server/main.py`, inside `create_starlette_app`, only include `Middleware(HostApiMiddleware, base_url=base_url)` in `final_middlewares` when `GLOBAL_SETTINGS.ENABLE_HOST` is truthy.
""",
        "regression_test": """from pathlib import Path

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
""",
    },
    "80c9144c": {
        "difficulty": "hard",
        "subset": ["marimo/_server/api/endpoints/ws/session_handler.py", "marimo/_session/session.py", "marimo/_session/types.py", "tests/_server/api/endpoints/test_ws.py"],
        "instruction": """# Task: Preserve session TTL across reconnects (`connection_generation`)

## Problem Description
When a client disconnects from a Marimo session (`SessionHandler._on_disconnect`), a TTL timer callback `_close()` is scheduled via `call_later(ttl_seconds, _close)`. If a new consumer B reconnects to the same `session_id` and then disconnects again before consumer A's original TTL timer fires, consumer A's stale `_close()` callback sees `live.connection_state() != ConnectionState.OPEN` and prematurely kills consumer B's session before B's own TTL window expires!

## Requirements
1. In `marimo/_session/types.py`, add `connection_generation: int` to the `Session` protocol.
2. In `marimo/_session/session.py`, initialize `self.connection_generation = 0` in `SessionImpl.__init__`, and increment `self.connection_generation += 1` inside `SessionImpl.connect_consumer` whenever `main` is truthy (`if main:`).
3. In `marimo/_server/api/endpoints/ws/session_handler.py`, inside `_on_disconnect` when `should_ttl_close` is true:
   - Capture `connection_generation = session.connection_generation` when scheduling `_close`.
   - At the start of `_close()`, look up `live = self.manager.get_session(self.params.session_id)` and return immediately if `live is None or live is not session or live.connection_generation != connection_generation`.
""",
        "regression_test": """from pathlib import Path

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
""",
    },
}

def main() -> int:
    dataset_root = REPO2BENCH_ROOT / "datasets" / "repo2bench-v1.0"
    if dataset_root.exists():
        shutil.rmtree(dataset_root)
    dataset_root.mkdir(parents=True, exist_ok=True)

    wanted_shas = set(TASK_SPECS.keys())
    mined_by_sha: dict[str, MinedCommit] = {}

    for repo_name, repo_path in [
        ("pydantic/pydantic-ai", Path("/tmp/repo_clones/pydantic-ai")),
        ("marimo-team/marimo", Path("/tmp/repo_clones/marimo")),
    ]:
        cands = mine_repository(
            repo_path,
            repo_name=repo_name,
            since="2026-01-01",
            max_commits_scan=600,
            limit=50,
        )
        for c in cands:
            short = c.commit_sha[:8]
            if short in wanted_shas:
                mined_by_sha[short] = c

    print(f"Matched {len(mined_by_sha)} / {len(wanted_shas)} target commits.")
    if len(mined_by_sha) != len(wanted_shas):
        missing = wanted_shas - set(mined_by_sha.keys())
        raise RuntimeError(f"Missing target commits: {missing}")

    emitted_dirs = []
    for sha8, spec in TASK_SPECS.items():
        commit = mined_by_sha[sha8]
        commit.difficulty = spec["difficulty"]
        tdir = emit_harbor_task(
            commit,
            dataset_root,
            custom_instruction=spec["instruction"],
            subset_paths=spec["subset"],
            regression_test_code=spec["regression_test"],
            base_image="repo2bench/python-base:3.12",
        )
        emitted_dirs.append(tdir)
        print(f"  Emitted [{commit.difficulty:6s}] {tdir.name}")

    print("\nRunning Fail -> Pass (nop == 0.0 -> oracle == 1.0) validation across all 20 tasks...")
    results = validate_dataset(dataset_root)
    passed = 0
    for r in results:
        status = "PASS" if r.valid and r.nop_pass_rate == 0.0 and r.oracle_pass_rate == 1.0 else "FAIL"
        if status == "PASS":
            passed += 1
        print(
            f"  [{status}] {r.task_id:56s} | nop={r.nop_pass_rate:.2f} (0/{r.nop_tests_total}) -> "
            f"oracle={r.oracle_pass_rate:.2f} ({r.oracle_tests_total}/{r.oracle_tests_total})"
            + (f" | err={r.error}" if r.error else "")
        )

    print(f"\nValidation Summary: {passed} / {len(results)} tasks passed strict Fail -> Pass gate.")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())

