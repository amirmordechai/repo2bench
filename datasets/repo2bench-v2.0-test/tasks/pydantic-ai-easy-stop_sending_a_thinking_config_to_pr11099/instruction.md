# Goal: Prevent sending thinking configurations to `gemini-2.5-flash-image` models

## Context & Goal
Both the Gemini API and Vertex AI reject any `thinkingConfig` (`includeThoughts` / `thinkingBudget`) on `gemini-2.5-flash-image` models with a 400 error (`Thinking is not enabled for this model`). Currently, Google model profile resolution enables `supports_thinking=True` for all `gemini-2.5-*` models indiscriminately.

## Acceptance Criteria
- Update Google model profile resolution so any model name containing `'gemini-2.5-flash-image'` sets `supports_thinking = False` and `google_supports_thinking_level = False`.
- All other Gemini 2.5 models (e.g. `'gemini-2.5-flash'`, `'gemini-2.5-pro'`) must continue to report `supports_thinking = True` and `google_supports_thinking_level = False`, while Gemini 3+ models report both as `True`.
