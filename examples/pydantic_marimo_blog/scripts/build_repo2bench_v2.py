#!/usr/bin/env python3
"""Build and validate the 30-task `repo2bench-v2.0` dataset (Option A: 10 Train + 20 Held-Out Test).

Key Methodological Upgrades over v1.0:
1. Chronological Split (Zero Data Science Leakage):
   - `datasets/repo2bench-v2.0-train` (10 older PRs: 5 pydantic-ai + 5 marimo) used ONLY for Harness² optimization.
   - `datasets/repo2bench-v2.0-test` (20 newer Held-Out PRs: 10 pydantic-ai + 10 marimo) used for blind evaluation.
2. Pre-Commit Black-Box Goal Prompts (Zero Solution / File-Path Leakage):
   - Every `instruction.md` is written as a pre-commit problem/goal description without file paths,
     line numbers, or commit-message implementation spoilers.
3. Broad Multi-Module Workspaces (30-120 files per task):
   - Each task packs entire package subdirectories so the agent must genuinely search the repository
     (`grep`, `find`, `view_file`) to localize the bug or feature entrypoint.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

REPO2BENCH_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO2BENCH_ROOT / "src"))
sys.path.insert(0, str(REPO2BENCH_ROOT))

from repo2bench.git_miner import MinedCommit, mine_repository
from repo2bench.harbor_emitter import emit_harbor_task
from repo2bench.validator import validate_dataset
from scripts.build_repo2bench_v1 import TASK_SPECS as V1_SPECS


# =============================================================================
# 10 CHRONOLOGICAL TRAIN TASKS (Older PRs: 5 pydantic-ai + 5 marimo)
# =============================================================================
TRAIN_SPECS: dict[str, dict] = {
    "ee573aca": {
        "difficulty": "easy",
        "subset": [
            "pydantic_ai_slim/pydantic_ai/providers",
            "pydantic_ai_slim/pydantic_ai/profiles",
            "tests/profiles",
        ],
        "instruction": """# Goal: Support `NativeOutput` structured schemas on every Fireworks model

## Context & Goal
Fireworks enforces JSON schema structured output at the platform level through its OpenAI-compatible `response_format` parameter, even for model families whose default family profile does not claim `supports_json_schema_output=True`. Currently, configuring `NativeOutput` on an unprofiled or Qwen-family model through `FireworksProvider` fails profile resolution because the provider's `model_profile` merges only `OpenAIModelProfile` and the family profile without enabling JSON schema output support across all Fireworks models (while leaving `supports_json_object_output` governed by the family profile so `PromptedOutput` behavior is unchanged).

## Acceptance Criteria
- Every model resolved through `FireworksProvider.model_profile(...)` must report `supports_json_schema_output=True` so `NativeOutput` works on all Fireworks models.
- Family-specific `supports_json_object_output` settings must remain unchanged so `PromptedOutput` resolution is not altered.
""",
        "regression_test": """from pathlib import Path

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
""",
    },
    "124b806e": {
        "difficulty": "easy",
        "subset": [
            "pydantic_ai_slim/pydantic_ai/models",
            "pydantic_ai_slim/pydantic_ai/_utils.py",
        ],
        "instruction": """# Goal: Use the canonical tool-call ID prefix constant when filtering synthesized Gemini server-side tool parts

## Context & Goal
When reconstructing message history for Google Gemini models, server-side tool parts (`grounding_metadata` / `url_context_metadata`) that were synthesized locally by Pydantic AI have generated tool call IDs beginning with `_utils.TOOL_CALL_ID_PREFIX` and must not be echoed back to Gemini. Currently, `_can_echo_server_side_tool_part` checks a hardcoded string literal prefix instead of referencing `_utils.TOOL_CALL_ID_PREFIX`.

## Acceptance Criteria
- Ensure `_can_echo_server_side_tool_part` checks `_utils.TOOL_CALL_ID_PREFIX` rather than a hardcoded string literal when deciding whether a `tool_call_id` can be echoed back to Gemini.
""",
        "regression_test": """from pathlib import Path

def _get_google_model_src() -> str:
    p = Path("/workspace/pydantic_ai_slim/pydantic_ai/models/google.py")
    if not p.is_file():
        p = Path("pydantic_ai_slim/pydantic_ai/models/google.py")
    return p.read_text(encoding="utf-8")

def test_uses_tool_call_id_prefix_constant():
    src = _get_google_model_src()
    part = src.split("def _can_echo_server_side_tool_part(", 1)[1].split("def ", 1)[0]
    assert "_utils.TOOL_CALL_ID_PREFIX" in part or "TOOL_CALL_ID_PREFIX" in part
    assert "startswith('pyd_ai_')" not in part and 'startswith("pyd_ai_")' not in part
""",
    },
    "bae7840a": {
        "difficulty": "medium",
        "subset": [
            "src/pydantic_ai_harness/pydantic_ai_harness/github",
            "src/pydantic_ai_harness/pydantic_ai_harness/_mcp.py",
        ],
        "instruction": """# Goal: Add `lockdown` support to the `GitHub` hosted MCP capability

## Context & Goal
GitHub's MCP server supports an `X-MCP-Lockdown: true` request header that asks GitHub to withhold issue, pull request, and comment content in public repositories written by users without push access. The `GitHub` capability class currently supports `read_only`, `toolsets`, `url`, and `client`, but does not expose a `lockdown: bool = False` option.

## Acceptance Criteria
1. Add `lockdown: bool = False` to the `GitHub` capability dataclass.
2. When `lockdown=True` is passed with a custom `client` (`self.client is not None`), raise `UserError` stating that `client` owns the connection and cannot be combined with `auth`, `url`, `toolsets`, or `lockdown`.
3. When building headers for the hosted MCP connection, include `'X-MCP-Lockdown': 'true'` whenever `self.lockdown` is truthy.
""",
        "regression_test": """from pathlib import Path

def _get_gh_src() -> str:
    p = Path("/workspace/src/pydantic_ai_harness/pydantic_ai_harness/github/_capability.py")
    if not p.is_file():
        p = Path("src/pydantic_ai_harness/pydantic_ai_harness/github/_capability.py")
    return p.read_text(encoding="utf-8")

def test_lockdown_field_added():
    src = _get_gh_src()
    assert "lockdown: bool = False" in src

def test_post_init_rejects_client_with_lockdown():
    src = _get_gh_src()
    post_part = src.split("def __post_init__", 1)[1].split("def ", 1)[0]
    assert "self.lockdown" in post_part
    assert "lockdown" in post_part

def test_lockdown_header_sent():
    src = _get_gh_src()
    assert "X-MCP-Lockdown" in src
    assert "if self.lockdown:" in src
""",
    },
    "a500320d": {
        "difficulty": "medium",
        "subset": [
            "src/pydantic_ai_harness/pydantic_ai_harness/e2b_sandbox",
        ],
        "instruction": """# Goal: Make `E2BSandboxBackend` raise a clear `UserError` under Trio before making any E2B SDK request

## Context & Goal
The E2B Python SDK runs every HTTP and RPC request on the `asyncio` event loop. Previously, only `run()` checked `running_on_asyncio()`, so calling filesystem methods (`read_bytes`, `write_bytes`, `stat`, `list_dir`, `make_dir`, `remove`, `exists`), sandbox acquisition (`_acquire`), or `kill_sandbox()` under Trio reached the E2B SDK and failed with confusing internal loop or timeout errors.

## Acceptance Criteria
1. Implement an asyncio check helper (e.g. `_require_asyncio()`) that raises `UserError('E2B needs the asyncio event loop: the E2B SDK runs every request on asyncio.')` when `not running_on_asyncio()`.
2. Ensure sandbox acquisition (`_acquire`), `kill_sandbox`, and all backend operations (`read_bytes`, `write_bytes`, `stat`, `list_dir`, `make_dir`, `remove`, `exists`, `run`) verify that they are running on `asyncio` before making any E2B request (even when using a caller-supplied `sandbox`), while `get_sandbox()` itself still returns a caller-supplied `self._sandbox` without raising.
""",
        "regression_test": """from pathlib import Path

def _get_e2b_src() -> str:
    p = Path("/workspace/src/pydantic_ai_harness/pydantic_ai_harness/e2b_sandbox/_backend.py")
    if not p.is_file():
        p = Path("src/pydantic_ai_harness/pydantic_ai_harness/e2b_sandbox/_backend.py")
    return p.read_text(encoding="utf-8")

def test_require_asyncio_raises_user_error():
    src = _get_e2b_src()
    assert "E2B needs the asyncio event loop: the E2B SDK runs every request on asyncio." in src

def test_kill_sandbox_and_acquire_check_asyncio():
    src = _get_e2b_src()
    kill_part = src.split("async def kill_sandbox(", 1)[1]
    assert "_require_asyncio()" in kill_part or "running_on_asyncio()" in kill_part

def test_filesystem_operations_guarded_for_asyncio():
    src = _get_e2b_src()
    for method in ("def read_bytes(", "def write_bytes(", "def stat(", "def list_dir("):
        part = src.split(method, 1)[1].split("async def ", 1)[0]
        assert "_sandbox_for_operation()" in part or "_require_asyncio()" in part
""",
    },
    "3491aaa4": {
        "difficulty": "hard",
        "subset": [
            "pydantic_ai_slim/pydantic_ai/models",
        ],
        "instruction": """# Goal: Accept unrounded float probabilities and scores from `SystemOneModel` backends such as vLLM

## Context & Goal
`SystemOneModel` validates that returned `ChoiceAnswer` and `ScoreAnswer` probabilities and expected scores match within display-rounding intervals (`_probability_bounds` and `_score_fits`). While the hosted Jev backend rounds probabilities to 2 decimal places, self-hosted backends like vLLM return unrounded float32/float64 softmax probabilities with many decimal digits. Because `_probability_bounds` and `_score_fits` compute half-unit intervals from the number of printed decimal places, unrounded floats get an interval narrower than float32 arithmetic error (`~1e-7`), causing valid vLLM responses to fail with `UnexpectedModelBehavior`.

## Acceptance Criteria
1. Define `_FLOAT_TOLERANCE = Decimal('1e-6')` in the SystemOne model module and accept a `float_tolerance: Decimal = Decimal(0)` keyword argument in `_probability_bounds` and `_score_fits` in the decision model module.
2. Ensure each probability and score half-unit interval in `_probability_bounds` and `_score_fits` is at least `float_tolerance` wide (`max(..., float_tolerance)`), and pass `float_tolerance=_FLOAT_TOLERANCE` from `SystemOneModel`.
""",
        "regression_test": """from pathlib import Path
from decimal import Decimal

def _read(rel: str) -> str:
    p = Path("/workspace") / rel
    if not p.is_file():
        p = Path(rel)
    return p.read_text(encoding="utf-8")

def test_decision_bounds_accept_float_tolerance():
    src = _read("pydantic_ai_slim/pydantic_ai/models/decision.py")
    assert "float_tolerance: Decimal = Decimal(0)" in src
    assert "max(" in src and "float_tolerance" in src

def test_system_one_passes_float_tolerance():
    src = _read("pydantic_ai_slim/pydantic_ai/models/system_one.py")
    assert "_FLOAT_TOLERANCE" in src
    assert "float_tolerance=_FLOAT_TOLERANCE" in src
""",
    },
    "342acf57": {
        "difficulty": "easy",
        "subset": [
            "marimo/_plugins/stateless",
            "marimo/_plugins/core",
        ],
        "instruction": """# Goal: Avoid division by zero when normalizing silent audio arrays in `mo.audio`

## Context & Goal
When a user passes an all-zero (silent) NumPy array to `mo.audio(np.zeros(8), rate=44100)` with normalization enabled (`normalize=True`), WAV conversion computes `max_abs_value = np.max(np.abs(data))`, which is `0.0`, and divides the audio samples by that zero peak amplitude. This emits runtime invalid-division / invalid-cast warnings and raises `FloatingPointError` under `np.errstate(invalid="raise")`.

## Acceptance Criteria
- When normalizing audio data to WAV, if `max_abs_value` is `0` (or not strictly positive), use a normalization divisor of `1` so silent mono or stereo arrays remain zero without dividing by zero.
""",
        "regression_test": """from pathlib import Path

def _get_audio_src() -> str:
    p = Path("/workspace/marimo/_plugins/stateless/audio.py")
    if not p.is_file():
        p = Path("marimo/_plugins/stateless/audio.py")
    return p.read_text(encoding="utf-8")

def test_zero_max_abs_value_returns_one():
    src = _get_audio_src()
    part = src.split("def convert_numpy_to_wav(", 1)[1].split("def _make_audio_element(", 1)[0]
    assert "max_abs_value > 0" in part or "max_abs_value != 0" in part
""",
    },
    "ca6dd42d": {
        "difficulty": "easy",
        "subset": [
            "marimo/_ast",
        ],
        "instruction": """# Goal: Preserve SQL table/view definitions in `find_sql_defs` when DuckDB emits comment tokens

## Context & Goal
In DuckDB 2, `duckdb.tokenize(sql_statement)` emits SQL comments (`-- ...` or `/* ... */`) as tokens with type `duckdb.token_type.comment`. When a comment appears before or inside a `CREATE TABLE` / `CREATE VIEW` statement (or between qualified name segments like `schema./*c*/tbl`), `find_sql_defs` fails to match the `CREATE` token sequence and drops or truncates the created table/view definition.

## Acceptance Criteria
- In `find_sql_defs`, filter out comment tokens (`getattr(duckdb.token_type, "comment", None)`) from the token list returned by `duckdb.tokenize(sql_statement)` before passing `tokens` to `_TokenExtractor`, while remaining compatible with DuckDB versions that do not define `token_type.comment`.
""",
        "regression_test": """from pathlib import Path

def _get_sql_visitor_src() -> str:
    p = Path("/workspace/marimo/_ast/sql_visitor.py")
    if not p.is_file():
        p = Path("marimo/_ast/sql_visitor.py")
    return p.read_text(encoding="utf-8")

def test_find_sql_defs_filters_duckdb_comment_tokens():
    src = _get_sql_visitor_src()
    part = src.split("def find_sql_defs(", 1)[1].split("def ", 1)[0]
    assert '"comment"' in part or "'comment'" in part
    assert "tokens" in part
""",
    },
    "f4f28449": {
        "difficulty": "medium",
        "subset": [
            "marimo/_export",
        ],
        "instruction": """# Goal: Skip hosted lockfile PEP 723 dependency pinning during offline WASM exports

## Context & Goal
When exporting a notebook to WASM (`export_wasm` and `_export_wasm_with_execution`), `pin_pep723_dependencies_for_wasm` currently pins inline PEP 723 script dependencies before calling `_prepare_wasm_export`. However, when `request.offline_export_dir` is provided (an offline / air-gapped WASM export), pinning against the hosted lockfile or host machine versions rewrites dependencies like `numpy` to versions Pyodide cannot install from the offline wheel mirror.

## Acceptance Criteria
1. Move the `pin_pep723_dependencies_for_wasm(code, request.path)` call into `_prepare_wasm_export(code, request)` and run it **only** when `request.offline_export_dir is None`.
2. Remove the unconditional `pin_pep723_dependencies_for_wasm` calls from `export_wasm` and `_export_wasm_with_execution`.
""",
        "regression_test": """from pathlib import Path

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
""",
    },
    "516b34fd": {
        "difficulty": "medium",
        "subset": [
            "marimo/_cli",
        ],
        "instruction": """# Goal: Handle arbitrary non-encodable Unicode characters in CLI `echo` fallback on non-UTF-8 streams

## Context & Goal
When `marimo convert` or `marimo check` prints output via `echo(*args, **kwargs)` on a non-UTF-8 terminal (such as Windows `cp1252`), `echo` catches `UnicodeEncodeError` and replaces six known characters (`→ ← ✓ ✗ • …`) with ASCII equivalents. However, if the text contains any other character outside the stream's encoding (such as a Unicode minus sign `−` or emoji), the retry inside the `except UnicodeEncodeError:` block raises `UnicodeEncodeError` again and crashes the CLI.

## Acceptance Criteria
1. When `UnicodeEncodeError` occurs in `echo()`, after replacing the six known symbols (`→` -> `->`, `←` -> `<-`, `✓` -> `v`, `✗` -> `x`, `•` -> `*`, `…` -> `...`), determine the target stream's encoding (`kwargs.get("file")`, or `sys.stderr` if `kwargs.get("err")` else `sys.stdout`, defaulting to `"ascii"`) and backslash-escape any remaining unencodable characters using `.encode(encoding, errors="backslashreplace").decode(encoding)`.
""",
        "regression_test": """from pathlib import Path
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
""",
    },
    "9c37a417": {
        "difficulty": "hard",
        "subset": [
            "marimo/_ast",
        ],
        "instruction": """# Goal: Handle multi-byte UTF-8 characters properly when `_TokenExtractor` slices SQL tokens

## Context & Goal
DuckDB's SQL tokenizer (`duckdb.tokenize`) reports token start offsets as **UTF-8 byte offsets**, not Python Unicode character indices. In `_TokenExtractor`, `self.sql_statement` is currently stored and sliced as a Python `str`. Whenever a SQL query contains multi-byte UTF-8 characters (such as accented letters, CJK characters, or emojis in comments/strings) before a `CREATE TABLE` or identifier token, `token_str(i)` slices at the wrong offset and corrupts extracted table/view names.

## Acceptance Criteria
- Store `self.sql_statement = sql_statement.encode("utf-8")` as UTF-8 `bytes` in `_TokenExtractor.__init__`, perform quote/whitespace matching in `token_str(i)` on the UTF-8 byte sequence (`b'"'`, `b"'"`, `b"e'"`, `rb"[\\s\\-/]"`), and `.decode("utf-8")` the returned slice.
""",
        "regression_test": """from pathlib import Path
import ast, re
from typing import Any

def _load_token_extractor():
    p = Path("/workspace/marimo/_ast/sql_visitor.py")
    if not p.is_file():
        p = Path("marimo/_ast/sql_visitor.py")
    src = p.read_text(encoding="utf-8")
    tree = ast.parse(src)
    ns = {"Any": Any, "re": re}
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "_TokenExtractor":
            exec(compile(ast.Module(body=[node], type_ignores=[]), str(p), "exec"), ns)
            return ns["_TokenExtractor"]
    raise AssertionError("_TokenExtractor not found")

def test_utf8_byte_offsets_extracted_correctly():
    cls = _load_token_extractor()
    sql = "-- café résumé ☕\\nCREATE TABLE my_tbl AS SELECT 1"
    byte_start = sql.encode("utf-8").index(b"my_tbl")
    ext = cls(sql, [(byte_start, 0)])
    assert ext.token_str(0) == "my_tbl"

def test_quoted_identifier_after_multibyte_comment():
    cls = _load_token_extractor()
    sql = "/* 日本語 */ CREATE TABLE \\"quoted_tbl\\" AS SELECT 1"
    byte_start = sql.encode("utf-8").index(b'"quoted_tbl"')
    ext = cls(sql, [(byte_start, 0)])
    assert ext.token_str(0) == '"quoted_tbl"'
""",
    },
}


# =============================================================================
# 20 HELD-OUT TEST TASKS (Pre-Commit Black-Box Prompts + Broad Workspaces)
# =============================================================================
TEST_PROMPT_OVERRIDES: dict[str, dict] = {
    "ca7dc6c4": {
        "difficulty": "easy",
        "subset": [
            "pydantic_ai_slim/pydantic_ai/profiles",
            "pydantic_ai_slim/pydantic_ai/models",
            "pydantic_ai_slim/pydantic_ai/providers",
        ],
        "instruction": """# Goal: Prevent sending thinking configurations to `gemini-2.5-flash-image` models

## Context & Goal
Both the Gemini API and Vertex AI reject any `thinkingConfig` (`includeThoughts` / `thinkingBudget`) on `gemini-2.5-flash-image` models with a 400 error (`Thinking is not enabled for this model`). Currently, Google model profile resolution enables `supports_thinking=True` for all `gemini-2.5-*` models indiscriminately.

## Acceptance Criteria
- Update Google model profile resolution so any model name containing `'gemini-2.5-flash-image'` sets `supports_thinking = False` and `google_supports_thinking_level = False`.
- All other Gemini 2.5 models (e.g. `'gemini-2.5-flash'`, `'gemini-2.5-pro'`) must continue to report `supports_thinking = True` and `google_supports_thinking_level = False`, while Gemini 3+ models report both as `True`.
""",
    },
    "3ea7e54e": {
        "difficulty": "medium",
        "subset": [
            "pydantic_ai_slim/pydantic_ai/agent",
            "pydantic_ai_slim/pydantic_ai/result.py",
            "pydantic_ai_slim/pydantic_ai/_agent_graph.py",
        ],
        "instruction": """# Goal: Stop `run_stream` agent name inference from keeping `deps` alive in a frame reference cycle

## Context & Goal
When an agent runs via `run_stream()` with `infer_name=True` and `self.name is None`, inspecting the caller's execution frame (`frame := inspect.currentframe()`) leaves the local variable `frame` bound inside the async generator's frame across `yield`. Because `frame` references the generator's own frame (which holds `deps`), `deps` cannot be freed when `run_stream()` finishes until a full garbage collection sweep runs.

## Acceptance Criteria
- Break the reference cycle inside `run_stream` immediately after inferring the agent's name (`self._infer_name(frame.f_back)`) by deleting the local `frame` binding (`del frame`) before yielding the stream.
""",
    },
    "d64b3453": {
        "difficulty": "medium",
        "subset": [
            "src/pydantic_ai_harness/pydantic_ai_harness",
        ],
        "instruction": """# Goal: Redact `quote_plus`-encoded BrowserUse secrets and prevent encoded secret placeholders from overwriting raw secrets

## Context & Goal
When the BrowserUse integration redacts `sensitive_data` secrets in `browse_web` outputs (`_secret_placeholders`), two leaks can occur:
1. Blocked search navigation URLs format query parameters using `urllib.parse.quote_plus(value, errors='surrogatepass')` (turning spaces into `+` and special characters into `%XX`), which currently bypasses secret redaction.
2. If secret `b`'s raw value equals secret `a`'s JSON-escaped or URL-encoded form, populating raw and encoded forms in a single pass allows `a`'s encoded placeholder to overwrite `b`'s raw value mapping.

## Acceptance Criteria
- Ensure `_secret_placeholders` registers all `<secret>{key}</secret>` self-mappings and raw secret values in a first pass, and then registers both JSON-escaped (`json.dumps(value, ensure_ascii=False)[1:-1]`) and `quote_plus(value, errors='surrogatepass')` forms in a second pass using `setdefault` so raw secret mappings always take precedence.
""",
    },
    "218e6427": {
        "difficulty": "medium",
        "subset": [
            "pydantic_ai_slim/pydantic_ai",
        ],
        "instruction": """# Goal: Expose `DEFAULT_HTTP_LIMITS`, accept `transport=` in `create_async_httpx2_client()`, and apply default connection limits to retry transports

## Context & Goal
HTTP client creation and tenacity retry transports in `pydantic_ai` have two gaps:
1. `create_async_httpx2_client()` does not accept a custom `transport` keyword argument and does not define or export a shared `DEFAULT_HTTP_LIMITS` constant (`httpx2.Limits(max_connections=DEFAULT_MAX_CONNECTIONS, max_keepalive_connections=DEFAULT_MAX_KEEPALIVE_CONNECTIONS)`) in `__all__`.
2. When `HTTPX2TenacityTransport` and `AsyncHTTPX2TenacityTransport` create their default `httpx2.HTTPTransport` / `httpx2.AsyncHTTPTransport` (when `wrapped` is `None`), they do not pass `limits=DEFAULT_HTTP_LIMITS`.

## Acceptance Criteria
1. Define and export `DEFAULT_HTTP_LIMITS` in `__all__`, and add `transport: httpx2.AsyncBaseTransport | None = None` to `create_async_httpx2_client()`, forwarding `transport=transport` to `httpx2.AsyncClient(...)`.
2. Update `HTTPX2TenacityTransport` and `AsyncHTTPX2TenacityTransport` to pass `limits=DEFAULT_HTTP_LIMITS` when constructing default `httpx2.HTTPTransport` and `httpx2.AsyncHTTPTransport` instances.
""",
    },
    "5b3ede47": {
        "difficulty": "medium",
        "subset": [
            "pydantic_graph/pydantic_graph",
        ],
        "instruction": """# Goal: Prevent `bool` and `int` inputs from matching each other's `Literal` decision branches in `pydantic_graph`

## Context & Goal
In Python, `bool` is a subclass of `int` (`True == 1` and `False == 0`). When a graph decision node routes inputs across branches typed with `Literal[1]` vs. `Literal[True]` (or `Literal[0]` vs. `Literal[False]`), checking `inputs in get_args(branch_source)` routes `True` into `Literal[1]` and `1` into `Literal[True]`.

## Acceptance Criteria
- When matching a `Literal` decision branch in the graph builder (`elif get_origin(branch_source) is Literal:`), ensure `bool` inputs do not match non-bool `int` literal arguments and non-bool `int` inputs (including `IntEnum` values) do not match `bool` literal arguments.
""",
    },
    "21162072": {
        "difficulty": "medium",
        "subset": [
            "pydantic_ai_slim/pydantic_ai/realtime",
            "pydantic_ai_slim/pydantic_ai/models",
        ],
        "instruction": """# Goal: Deprecate `google_multi_speaker` on `GoogleRealtimeModel` and reject it with `UserError` before connecting

## Context & Goal
Gemini Live realtime models do not support `multi_speaker_voice_config`. Passing `google_multi_speaker` in `GoogleRealtimeModelSettings` currently constructs a `MultiSpeakerVoiceConfig` in `_speech_config()` that fails server-side during the WebSocket session instead of failing fast before dialing.

## Acceptance Criteria
1. Mark `MultiSpeaker` as `@deprecated(..., category=PydanticAIDeprecationWarning)`.
2. Remove `multi_speaker` / `MultiSpeakerVoiceConfig` handling from `_speech_config()` so it only configures `voice_config` (from `google_voice`) and `language_code` (from `google_language_code`).
3. Add a `_check_voice_settings(self, settings: GoogleRealtimeModelSettings) -> None` method on `GoogleRealtimeModel` (called before dialing) that raises `UserError` if `'google_multi_speaker' in settings`.
""",
    },
    "bfe3f6d6": {
        "difficulty": "medium",
        "subset": [
            "src/pydantic_ai_harness/pydantic_ai_harness",
        ],
        "instruction": """# Goal: Preserve dictionary key insertion order when serializing messages in `keyed_messages`

## Context & Goal
When step persistence serializes conversation messages via `keyed_messages(messages)` to compute SHA-256 digests and JSON payloads, sorting dictionary keys alters the key order of tool call arguments, tool return payloads, and `provider_details` when a snapshot is reloaded—invalidating downstream LLM prompt caches on resumed runs.

## Acceptance Criteria
- Update `keyed_messages(messages)` in the step persistence module so JSON serialization preserves original dictionary key insertion order while keeping compact separators (`separators=(',', ':')`).
""",
    },
    "e5d08153": {
        "difficulty": "hard",
        "subset": [
            "pydantic_ai_slim/pydantic_ai",
            "pydantic_graph/pydantic_graph",
        ],
        "instruction": """# Goal: Break reference cycles retaining `deps` in completed `GraphRun` and `ToolManager` executions

## Context & Goal
Completed `Agent.run` and `GraphBuilder` runs retain `deps` in memory until garbage collection runs due to two reference cycles:
1. `GraphRun` retains its internal iterator instance after `__aexit__` completes, holding bound callbacks that reference `GraphRun`.
2. `ToolManager.ctx` holds a `RunContext` whose `.tool_manager` attribute points back to the `ToolManager` instance across run steps and after the agent run exits.

## Acceptance Criteria
- Ensure `GraphRun` clears its iterator reference upon exiting `__aexit__`, and ensure `ToolManager` releases the cyclic `tool_manager` reference on its `RunContext` both when transitioning between run steps and when the agent run context stack exits.
""",
    },
    "3e3a6214": {
        "difficulty": "hard",
        "subset": [
            "pydantic_ai_slim/pydantic_ai/realtime",
            "pydantic_ai_slim/pydantic_ai/profiles",
        ],
        "instruction": """# Goal: Include `webrtc_url` on `RealtimeClientSecret` for OpenAI and Azure OpenAI WebRTC sessions

## Context & Goal
When a browser client uses an ephemeral `RealtimeClientSecret` minted by `OpenAIRealtimeModel`, it needs to know the endpoint URL where it should POST its WebRTC SDP offer (which differs between OpenAI and Azure OpenAI, and is `None` if the model profile does not support WebRTC).

## Acceptance Criteria
- Expose `webrtc_url: str | None = None` on `RealtimeClientSecret` and populate it during client secret minting when the model profile supports WebRTC.
""",
    },
    "5a09a0c8": {
        "difficulty": "hard",
        "subset": [
            "src/pydantic_clai2/pydantic_clai2",
        ],
        "instruction": """# Goal: Capture active web-serving handoff state before `/update` modifies installed packages on disk

## Context & Goal
When `clai2` runs `/update`, `uv` upgrades the package files on disk in-place while the session is still running. Inspecting the web-serving state *after* `uv` finishes can trigger lazy imports of newly upgraded modules whose symbols conflict with the in-memory session, crashing with `ImportError`.

## Acceptance Criteria
- Capture the active web-serving handoff state on the `Updates` controller *before* executing the `uv` upgrade command, only retain it when `relaunch` succeeds, and return that captured handoff from the session runtime.
""",
    },
    # --- 10 MARIMO HELD-OUT TEST TASKS ---
    "774844f9": {
        "difficulty": "easy",
        "subset": [
            "marimo/_utils",
        ],
        "instruction": """# Goal: Accept single-digit port numbers in URL validation (`is_url`)

## Context & Goal
Local and custom HTTP/HTTPS URLs that use single-digit ports (such as `http://127.0.0.1:8/macros.tex` or `http://localhost:9/test`) are currently rejected by `is_url` because the port regular expression requires at least 2 digits.

## Acceptance Criteria
- Update URL validation in `is_url` so ports from 1 to 5 digits (`:1` through `:65535`) are accepted on valid URLs, while non-URLs and 6-digit ports remain rejected.
""",
    },
    "c716635c": {
        "difficulty": "easy",
        "subset": [
            "marimo/_plugins/core",
            "marimo/_plugins/ui",
        ],
        "instruction": """# Goal: Escape square brackets in web component attribute values (`_build_attr`) so Markdown links do not corrupt widgets

## Context & Goal
When a Marimo UI element or web component is embedded inside Markdown (`mo.md`), `_build_attr(name, value)` escapes backslashes (`&#92;`) and dollar signs (`&#36;`) so LaTeX and escape sequences do not corrupt `data-*` attributes. However, unescaped square brackets (`[` and `]`) in values like `"C[A](C)"` or `"[a][b]"` are parsed as Markdown links, breaking widget initialization.

## Acceptance Criteria
- Update `_build_attr` so `[` is replaced with `"&#91;"` and `]` is replaced with `"&#93;"` in the serialized attribute value alongside `$` and `\\`.
""",
    },
    "5e8e83e4": {
        "difficulty": "medium",
        "subset": [
            "marimo/_utils",
            "marimo/_Inspector",
        ],
        "instruction": """# Goal: Preserve underscores inside inline code spans when converting Markdown docstrings (`MarkdownConverter`)

## Context & Goal
When converting docstrings that are already plain Markdown containing backtick code spans (e.g. ``Use `shout_factor` ``) without structured RST/Google/NumPy docstring sections, default docstring converters escape underscores inside backtick spans (`shout\\_factor`).

## Acceptance Criteria
- Add a `MarkdownConverter` class (with `priority = 0`, `can_convert(self, docstring: str) -> bool` matching unescaped closed backtick code spans across single or multiple lines, and `convert(self, docstring: str) -> str` returning `docstring` unchanged) right after `MarimoConverter`.
""",
    },
    "c15169de": {
        "difficulty": "medium",
        "subset": [
            "marimo/_sql",
        ],
        "instruction": """# Goal: Align DuckDB SQL error column offsets when multiple `{...}` interpolations precede a syntax error

## Context & Goal
When `_parse_sql_duckdb` sanitizes `{...}` Python interpolations in a SQL query, `idx_to_offset_dict` records each replacement index `idx` in the *original* SQL string and the added quote length `offset`. However, DuckDB's `error_line_start` and `position` are in the *sanitized* SQL coordinate system. Comparing `error_line_start <= idx < position` directly against the unadjusted `idx` miscalculates the error column offset whenever earlier `{...}` interpolations shift the sanitized positions.

## Acceptance Criteria
- Track `preceding_offset = 0` while iterating `for idx, offset in idx_to_offset_dict.items():`, compute `sanitized_idx = idx + preceding_offset`, increment `preceding_offset += offset`, and check `if error_line_start <= sanitized_idx < position:` when accumulating `cumulative_offset`.
""",
    },
    "ca983d9b": {
        "difficulty": "medium",
        "subset": [
            "marimo/_save",
        ],
        "instruction": """# Goal: Fall back to `pickle` serialization in `LazyLoader` when a typed blob serializer fails

## Context & Goal
In `LazyLoader.save_cache`, `_put_or_mark_unserializable` currently takes a single `serialize` callable and immediately marks a cached variable as unserializable if its primary typed serializer (such as Arrow/Parquet on a mixed-dtype Pandas column) raises an exception, instead of falling back to `pickle.dumps`.

## Acceptance Criteria
1. Change `_put_or_mark_unserializable`'s third parameter to `loader: str` and try `serializers = {loader: BLOB_SERIALIZERS.get(loader, pickle.dumps), "pickle": pickle.dumps}` in order.
2. When a fallback `suffix != loader` succeeds, update `key = Path(key).with_suffix(f".{suffix}").as_posix()` and update `item.reference = key` for `item in items` before storing `store.put(key, data)`, and update callers in `LazyLoader` to pass loader name strings (`return_loader`, `"pickle"`, `loader`).
""",
    },
    "d0b73b93": {
        "difficulty": "hard",
        "subset": [
            "marimo/_ast",
        ],
        "instruction": """# Goal: Exclude DML CTE aliases and respect CTE scope rules in `find_sql_refs`

## Context & Goal
`find_sql_refs(sql_statement)` currently misidentifies CTE aliases in DML queries (such as `WITH changed AS (INSERT INTO items VALUES (1) RETURNING *) SELECT * FROM changed`) or nested subquery CTEs as external table dependencies because `build_scope` exposes DML CTEs as plain `exp.Table` sources and `_collect_table_refs_excluding_ctes` only checks top-level `WITH` clauses.

## Acceptance Criteria
1. Inside `find_sql_refs`, implement `is_cte_reference(table: exp.Table) -> bool` that returns `False` for qualified tables (`table.db or table.catalog`) or direct targets of `exp.Insert, exp.Update, exp.Delete`, and walks ancestor `with_` clauses respecting `with_clause.args.get("recursive")` and `cte.alias.lower() == table_name`.
2. Filter with `not is_cte_reference(table)` in `_collect_table_refs_excluding_ctes` and skip `source` during `build_scope` traversal when `requires_table_scan and is_cte_reference(source)`.
""",
    },
    "330ca411": {
        "difficulty": "medium",
        "subset": [
            "marimo/_sql",
        ],
        "instruction": """# Goal: Preserve `sql_line`, `sql_col`, `hint`, and `sql_statement` when re-raising or formatting `MarimoSQLException`

## Context & Goal
When a SQL engine raises a `MarimoSQLException` that already carries structured error location fields (`sql_line`, `sql_col`, `sql_statement`, `hint`), two places accidentally strip those fields:
1. In `sql()`, when `is_sql_parse_error(e)` is true, it constructs a new `MarimoSQLException(message=str(e), sql_statement=query)` without preserving `e.sql_statement or query`, `e.sql_line`, `e.sql_col`, and `e.hint` when `isinstance(e, MarimoSQLException)`.
2. In `create_sql_error_from_exception()`, it only checks `if isinstance(exception, MarimoSQLException) and exception.hint:`, dropping `sql_line` and `sql_col` whenever `exception.hint` is `None`.

## Acceptance Criteria
1. In `sql()`, when `is_sql_parse_error(e)` and `isinstance(e, MarimoSQLException)`, re-raise `MarimoSQLException` preserving `sql_statement=e.sql_statement or query`, `sql_line=e.sql_line`, `sql_col=e.sql_col`, and `hint=e.hint`.
2. In `create_sql_error_from_exception()`, preserve structured metadata whenever `isinstance(exception, MarimoSQLException)` and any of `exception.hint is not None`, `exception.sql_statement`, `exception.sql_line is not None`, or `exception.sql_col is not None` is truthy.
""",
    },
    "169d793c": {
        "difficulty": "medium",
        "subset": [
            "marimo/_plugins/ui/_impl/tables",
        ],
        "instruction": """# Goal: Pad unequal-length dictionary columns with `None` across `select_rows`, `select_cells`, and `search` in `DefaultTableManager`

## Context & Goal
When `DefaultTableManager` wraps column-oriented dictionary data where columns have unequal lengths (e.g. `{"a": [2], "b": [10, 20]}`), `sort_values` pads shorter columns with `None` up to `self.get_num_rows()`, but `select_rows`, `select_cells`, and `search` index directly into `self.data[key][row]` and crash with `IndexError: list index out of range`.

## Acceptance Criteria
- Add a `_padded_columns(self)` helper on `DefaultTableManager` that pads any column shorter than `self.get_num_rows()` with `[None] * (num_rows - len(values))` without mutating `self.data`, and use `self._padded_columns()` in `select_rows`, `select_cells`, `search`, and `sort_values`.
""",
    },
    "c6226418": {
        "difficulty": "hard",
        "subset": [
            "marimo/_config",
            "marimo/_server",
        ],
        "instruction": """# Goal: Gate the experimental host lifespan and `HostApiMiddleware` behind `MARIMO_ENABLE_HOST`

## Context & Goal
Marimo's experimental host integration (`host` server lifespan and `HostApiMiddleware`) currently runs unconditionally in `EDIT` mode on every Starlette server instance. It should be disabled by default and only enabled when the `MARIMO_ENABLE_HOST` environment setting (`ENABLE_HOST` on `GLOBAL_SETTINGS`) is truthy.

## Acceptance Criteria
- Gate both the `host` lifespan and `HostApiMiddleware` registration in `create_starlette_app` behind `GLOBAL_SETTINGS.ENABLE_HOST` (`MARIMO_ENABLE_HOST`).
""",
    },
    "80c9144c": {
        "difficulty": "hard",
        "subset": [
            "marimo/_session",
            "marimo/_server/api/endpoints/ws",
        ],
        "instruction": """# Goal: Prevent stale disconnect TTL timers from closing a session after a new main consumer reconnects

## Context & Goal
When a client disconnects from a Marimo session (`_on_disconnect`), a delayed `_close()` callback is scheduled via `call_later(ttl_seconds, _close)`. If a new main consumer reconnects to the same session and then disconnects again before the first consumer's TTL timer expires, the first consumer's stale `_close()` callback sees the session closed/disconnected and prematurely terminates the second consumer's session before its own TTL expires.

## Acceptance Criteria
- Track a monotonic connection generation counter on the session whenever a main consumer connects, and ensure delayed disconnect `_close()` callbacks become no-ops if a newer main consumer connection occurred since the timer was scheduled.
""",
    },
}


def build_split(
    split_name: str,
    dataset_root: Path,
    specs: dict[str, dict],
    mined_by_sha: dict[str, MinedCommit],
) -> bool:
    if dataset_root.exists():
        shutil.rmtree(dataset_root)
    dataset_root.mkdir(parents=True, exist_ok=True)

    print(f"\n=== Building {split_name} ({len(specs)} tasks) -> {dataset_root} ===")
    for sha8, spec in specs.items():
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
        print(f"  Emitted [{commit.difficulty:6s}] {tdir.name}")

    print(f"\nValidating Fail -> Pass (nop == 0.0 -> oracle == 1.0) on {split_name}...")
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
    print(f"{split_name} Validation Summary: {passed} / {len(results)} passed.")
    return passed == len(results)


def main() -> int:
    # Merge V1_SPECS regression_test with TEST_PROMPT_OVERRIDES black-box instructions & broad subsets
    test_specs: dict[str, dict] = {}
    for sha8, v1 in V1_SPECS.items():
        ov = TEST_PROMPT_OVERRIDES[sha8]
        test_specs[sha8] = {
            "difficulty": ov["difficulty"],
            "subset": ov["subset"],
            "instruction": ov["instruction"],
            "regression_test": v1["regression_test"],
        }

    wanted_shas = set(TRAIN_SPECS.keys()) | set(test_specs.keys())
    mined_by_sha: dict[str, MinedCommit] = {}

    cache_root = Path.home() / ".cache" / "r2b_sources"
    for repo_name, repo_path in [
        ("pydantic/pydantic-ai", cache_root / "pydantic-ai"),
        ("marimo-team/marimo", cache_root / "marimo"),
    ]:
        cands = mine_repository(
            repo_path,
            repo_name=repo_name,
            since="2026-01-01",
            max_commits_scan=300,
            limit=80,
        )
        for c in cands:
            short = c.commit_sha[:8]
            if short in wanted_shas:
                mined_by_sha[short] = c

    print(f"Matched {len(mined_by_sha)} / {len(wanted_shas)} total target commits (10 Train + 20 Held-Out Test).")
    if len(mined_by_sha) != len(wanted_shas):
        missing = wanted_shas - set(mined_by_sha.keys())
        raise RuntimeError(f"Missing target commits: {missing}")

    ok_train = build_split(
        "repo2bench-v2.0-train",
        REPO2BENCH_ROOT / "datasets" / "repo2bench-v2.0-train",
        TRAIN_SPECS,
        mined_by_sha,
    )
    ok_test = build_split(
        "repo2bench-v2.0-test",
        REPO2BENCH_ROOT / "datasets" / "repo2bench-v2.0-test",
        test_specs,
        mined_by_sha,
    )
    return 0 if (ok_train and ok_test) else 1


if __name__ == "__main__":
    raise SystemExit(main())

