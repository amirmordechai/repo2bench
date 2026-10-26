# Goal: Use the canonical tool-call ID prefix constant when filtering synthesized Gemini server-side tool parts

## Context & Goal
When reconstructing message history for Google Gemini models, server-side tool parts (`grounding_metadata` / `url_context_metadata`) that were synthesized locally by Pydantic AI have generated tool call IDs beginning with `_utils.TOOL_CALL_ID_PREFIX` and must not be echoed back to Gemini. Currently, `_can_echo_server_side_tool_part` checks a hardcoded string literal prefix instead of referencing `_utils.TOOL_CALL_ID_PREFIX`.

## Acceptance Criteria
- Ensure `_can_echo_server_side_tool_part` checks `_utils.TOOL_CALL_ID_PREFIX` rather than a hardcoded string literal when deciding whether a `tool_call_id` can be echoed back to Gemini.
