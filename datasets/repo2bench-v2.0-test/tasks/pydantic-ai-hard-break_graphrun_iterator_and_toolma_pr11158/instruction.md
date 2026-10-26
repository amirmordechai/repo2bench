# Goal: Break reference cycles retaining `deps` in completed `GraphRun` and `ToolManager` executions

## Context & Goal
Completed `Agent.run` and `GraphBuilder` runs retain `deps` in memory until garbage collection runs due to two reference cycles:
1. `GraphRun` retains its internal iterator instance after `__aexit__` completes, holding bound callbacks that reference `GraphRun`.
2. `ToolManager.ctx` holds a `RunContext` whose `.tool_manager` attribute points back to the `ToolManager` instance across run steps and after the agent run exits.

## Acceptance Criteria
- Ensure `GraphRun` clears its iterator reference upon exiting `__aexit__`, and ensure `ToolManager` releases the cyclic `tool_manager` reference on its `RunContext` both when transitioning between run steps and when the agent run context stack exits.
