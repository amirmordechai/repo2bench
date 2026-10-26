# Task: Stop `clai2` from crashing with `ImportError` when it restarts after `/update`

## Problem Description
When `/update` runs `uv` to upgrade `clai2` in-place while a session is running, calling `web_serving(self.loader)` *after* `uv` has replaced the installed files on disk can trigger a lazy import of a newly upgraded module whose symbols conflict with the old in-memory modules, crashing with `ImportError`.

## Requirements
1. In `src/pydantic_clai2/pydantic_clai2/cli/self_update.py`:
   - Add `serving: Callable[[], WebHandoff | None] = lambda: None` and `web: WebHandoff | None = None` fields to `Updates`.
   - Inside `Updates.command()`, call `served = self.serving()` *before* running `uv` (`with CancelScope(shield=True):`), and after `self.relaunch = await self.locate(uv)` set `self.web = served if self.relaunch is not None else None`.
2. In `src/pydantic_clai2/pydantic_clai2/runtime/session_runtime.py`:
   - Wire `updates.serving = lambda: web_serving(loader)` in `create_shell`.
   - Update `SessionRuntime.handoff(self)` to return `self.updates.web`.
