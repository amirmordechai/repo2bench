# Task: Break `GraphRun` iterator and `ToolManager` context reference cycles

## Problem Description
Completed `Agent.run` and `GraphBuilder` runs retain `deps` in reference cycles until garbage collection runs because:
1. In `pydantic_graph/pydantic_graph/graph_builder.py`, `GraphRun._iterator_instance` holds bound callbacks referring back to `GraphRun`; `__aexit__` does not clear `self._iterator_instance = None` in a `finally:` block.
2. In `pydantic_ai_slim/pydantic_ai/tool_manager.py`, `ToolManager.ctx` refers to a `RunContext` whose `.tool_manager` refers back to `self`. `ToolManager` needs a `_release_context(self) -> None` method (`if self.ctx is not None and self.ctx.tool_manager is self: self.ctx = replace(self.ctx, tool_manager=None)`) called at the end of `for_run_step` and registered via `stack.callback(lambda: graph_deps.tool_manager._release_context())` in `_PreparedAgentRun` in `pydantic_ai_slim/pydantic_ai/agent/__init__.py`.

## Requirements
1. In `pydantic_graph/pydantic_graph/graph_builder.py`, ensure `GraphRun.__aexit__` sets `self._iterator_instance = None` in a `try ... finally:` block after awaiting `self._async_exit_stack.__aexit__(...)`, and assert `self._iterator_instance is not None` in `_iterator_context`.
2. In `pydantic_ai_slim/pydantic_ai/tool_manager.py`, implement `_release_context(self) -> None` on `ToolManager` and call `self._release_context()` in `for_run_step` before returning `new_tm`.
3. In `pydantic_ai_slim/pydantic_ai/agent/__init__.py`, register `stack.callback(lambda: graph_deps.tool_manager._release_context())` on the `AsyncExitStack` in `_PreparedAgentRun`.
