# Goal: Support `NativeOutput` structured schemas on every Fireworks model

## Context & Goal
Fireworks enforces JSON schema structured output at the platform level through its OpenAI-compatible `response_format` parameter, even for model families whose default family profile does not claim `supports_json_schema_output=True`. Currently, configuring `NativeOutput` on an unprofiled or Qwen-family model through `FireworksProvider` fails profile resolution because the provider's `model_profile` merges only `OpenAIModelProfile` and the family profile without enabling JSON schema output support across all Fireworks models (while leaving `supports_json_object_output` governed by the family profile so `PromptedOutput` behavior is unchanged).

## Acceptance Criteria
- Every model resolved through `FireworksProvider.model_profile(...)` must report `supports_json_schema_output=True` so `NativeOutput` works on all Fireworks models.
- Family-specific `supports_json_object_output` settings must remain unchanged so `PromptedOutput` resolution is not altered.
