# Goal: Capture active web-serving handoff state before `/update` modifies installed packages on disk

## Context & Goal
When `clai2` runs `/update`, `uv` upgrades the package files on disk in-place while the session is still running. Inspecting the web-serving state *after* `uv` finishes can trigger lazy imports of newly upgraded modules whose symbols conflict with the in-memory session, crashing with `ImportError`.

## Acceptance Criteria
- Capture the active web-serving handoff state on the `Updates` controller *before* executing the `uv` upgrade command, only retain it when `relaunch` succeeds, and return that captured handoff from the session runtime.
