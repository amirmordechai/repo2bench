# Goal: Preserve dictionary key insertion order when serializing messages in `keyed_messages`

## Context & Goal
When step persistence serializes conversation messages via `keyed_messages(messages)` to compute SHA-256 digests and JSON payloads, sorting dictionary keys alters the key order of tool call arguments, tool return payloads, and `provider_details` when a snapshot is reloaded—invalidating downstream LLM prompt caches on resumed runs.

## Acceptance Criteria
- Update `keyed_messages(messages)` in the step persistence module so JSON serialization preserves original dictionary key insertion order while keeping compact separators (`separators=(',', ':')`).
