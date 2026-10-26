# Goal: Make `E2BSandboxBackend` raise a clear `UserError` under Trio before making any E2B SDK request

## Context & Goal
The E2B Python SDK runs every HTTP and RPC request on the `asyncio` event loop. Previously, only `run()` checked `running_on_asyncio()`, so calling filesystem methods (`read_bytes`, `write_bytes`, `stat`, `list_dir`, `make_dir`, `remove`, `exists`), sandbox acquisition (`_acquire`), or `kill_sandbox()` under Trio reached the E2B SDK and failed with confusing internal loop or timeout errors.

## Acceptance Criteria
1. Implement an asyncio check helper (e.g. `_require_asyncio()`) that raises `UserError('E2B needs the asyncio event loop: the E2B SDK runs every request on asyncio.')` when `not running_on_asyncio()`.
2. Ensure sandbox acquisition (`_acquire`), `kill_sandbox`, and all backend operations (`read_bytes`, `write_bytes`, `stat`, `list_dir`, `make_dir`, `remove`, `exists`, `run`) verify that they are running on `asyncio` before making any E2B request (even when using a caller-supplied `sandbox`), while `get_sandbox()` itself still returns a caller-supplied `self._sandbox` without raising.
