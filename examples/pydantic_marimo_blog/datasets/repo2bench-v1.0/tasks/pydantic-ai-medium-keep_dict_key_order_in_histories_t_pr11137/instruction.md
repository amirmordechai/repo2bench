# Task: Keep dict key order in histories that step stores reload (`keyed_messages`)

## Problem Description
In `src/pydantic_ai_harness/pydantic_ai_harness/step_persistence/_messages.py`, `keyed_messages(messages)` currently serializes each message with:
`text = json.dumps(message, sort_keys=True, separators=(',', ':'))`
Sorting dictionary keys alters the key order of tool call arguments, tool return payloads, and `provider_details` when a snapshot is reloaded from step persistence, invalidating downstream provider prompt caches on resumed runs.

## Requirements
1. In `src/pydantic_ai_harness/pydantic_ai_harness/step_persistence/_messages.py`, remove `sort_keys=True` from `json.dumps(message, separators=(',', ':'))` inside `keyed_messages(messages)` so original dictionary key insertion order is preserved in both the stored JSON text and its SHA-256 hash.
