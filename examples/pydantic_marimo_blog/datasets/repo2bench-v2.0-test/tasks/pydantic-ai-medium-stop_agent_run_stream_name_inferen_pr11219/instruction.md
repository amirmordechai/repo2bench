# Goal: Stop `run_stream` agent name inference from keeping `deps` alive in a frame reference cycle

## Context & Goal
When an agent runs via `run_stream()` with `infer_name=True` and `self.name is None`, inspecting the caller's execution frame (`frame := inspect.currentframe()`) leaves the local variable `frame` bound inside the async generator's frame across `yield`. Because `frame` references the generator's own frame (which holds `deps`), `deps` cannot be freed when `run_stream()` finishes until a full garbage collection sweep runs.

## Acceptance Criteria
- Break the reference cycle inside `run_stream` immediately after inferring the agent's name (`self._infer_name(frame.f_back)`) by deleting the local `frame` binding (`del frame`) before yielding the stream.
