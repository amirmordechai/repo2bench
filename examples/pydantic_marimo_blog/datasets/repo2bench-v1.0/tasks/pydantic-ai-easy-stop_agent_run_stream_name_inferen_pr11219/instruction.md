# Task: Stop `Agent.run_stream` name inference from keeping `deps` alive until GC

## Problem Description
In `pydantic_ai_slim/pydantic_ai/agent/abstract.py`, inside `AbstractAgent.run_stream()`, when `infer_name and self.name is None` is true, `if frame := inspect.currentframe(): self._infer_name(frame.f_back)` leaves the local variable `frame` bound inside the async generator's frame. Because `frame` refers to the generator's own execution frame, it creates a reference cycle that keeps `deps` alive until garbage collection runs.

## Requirements
1. In `pydantic_ai_slim/pydantic_ai/agent/abstract.py`, inside `run_stream`'s `if infer_name and self.name is None:` block, explicitly `del frame` immediately after `if frame := inspect.currentframe(): self._infer_name(frame.f_back)`.
2. Ensure `run_stream` still calls `self._infer_name(frame.f_back)` when `frame` is not None and does not retain `frame` in local variables afterward.
