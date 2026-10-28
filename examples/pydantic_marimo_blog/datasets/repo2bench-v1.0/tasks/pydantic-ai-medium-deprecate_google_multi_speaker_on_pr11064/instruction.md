# Task: Deprecate `google_multi_speaker` on `GoogleRealtimeModel` and reject it before dialing

## Problem Description
No Gemini Live model supports multi-speaker voice configurations (`multi_speaker_voice_config`). In `pydantic_ai_slim/pydantic_ai/realtime/google.py`, `GoogleRealtimeModel` currently builds `MultiSpeakerVoiceConfig` in `_speech_config()` and does not reject `google_multi_speaker` before opening a WebSocket session.

## Requirements
1. In `pydantic_ai_slim/pydantic_ai/realtime/google.py`:
   - Decorate `MultiSpeaker` with `@deprecated(..., category=PydanticAIDeprecationWarning)` (importing `deprecated` from `typing_extensions`).
   - Simplify `_speech_config(self, model_settings: GoogleRealtimeModelSettings)` so it only builds `voice_config` from `google_voice` and `language_code` from `google_language_code` (returning `None` when both are absent, and no longer constructing `MultiSpeakerVoiceConfig`).
   - Add a `_check_voice_settings(self, settings: GoogleRealtimeModelSettings) -> None` method on `GoogleRealtimeModel` that raises `UserError` (`'`google_multi_speaker` is deprecated and not supported by any Gemini Live model...'`) if `'google_multi_speaker' in settings`, and also checks `google_affective_dialog`, calling `self._check_voice_settings(settings)` before dialing.
