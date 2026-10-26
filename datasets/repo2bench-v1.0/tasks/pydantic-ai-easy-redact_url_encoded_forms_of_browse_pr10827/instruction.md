# Task: Redact URL-encoded forms of `BrowserUse` secrets in `browse_web` results

## Problem Description
In `src/pydantic_ai_harness/pydantic_ai_harness/browser_use/_toolset.py`, `_secret_placeholders(sensitive_data)` builds a dictionary mapping each secret value and its JSON-escaped form to `<secret>{key}</secret>`. However:
1. When `browser-use` blocks a search navigation, it reports the URL built with `urllib.parse.quote_plus(value, errors='surrogatepass')` (e.g. `p%40ss+word` for `p@ss word`), leaking the URL-encoded secret.
2. If secret `b`'s raw value equals secret `a`'s encoded/escaped form, iterating raw and encoded forms in a single loop causes `a`'s encoded placeholder to overwrite `b`'s raw value placeholder.

## Requirements
1. Update `_secret_placeholders` in `src/pydantic_ai_harness/pydantic_ai_harness/browser_use/_toolset.py` to:
   - First register all `<secret>{key}</secret>` self-mappings and raw `value -> placeholder` mappings across all non-empty secrets.
   - Then in a second pass register `json.dumps(value, ensure_ascii=False)[1:-1]` and `quote_plus(value, errors='surrogatepass')` via `placeholders.setdefault(...)`.
