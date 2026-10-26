# Task: Stop sending a thinking config to `gemini-2.5-flash-image`

## Problem Description
In `pydantic_ai_slim/pydantic_ai/profiles/google.py`, `google_model_profile(model_name)` currently treats all `gemini-2.5-*` models as supporting thinking (`supports_thinking=True`). However, both the Gemini API and Vertex AI reject any thinking configuration (`thinkingConfig` / `includeThoughts` / `thinkingBudget`) for `gemini-2.5-flash-image` with a 400 error (`Thinking is not enabled for this model`).

## Requirements
1. Update `google_model_profile` in `pydantic_ai_slim/pydantic_ai/profiles/google.py` so that any model name containing `'gemini-2.5-flash-image'` sets `supports_thinking = False` and `google_supports_thinking_level = False` (just like Gemma and pre-Gemini-2.5 models).
2. Ensure other Gemini 2.5 models (such as `'gemini-2.5-flash'` and `'gemini-2.5-pro'`) continue to report `supports_thinking = True` and `google_supports_thinking_level = False`, while Gemini 3+ models report both as `True`.
