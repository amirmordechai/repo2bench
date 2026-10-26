# Goal: Deprecate `google_multi_speaker` on `GoogleRealtimeModel` and reject it with `UserError` before connecting

## Context & Goal
Gemini Live realtime models do not support `multi_speaker_voice_config`. Passing `google_multi_speaker` in `GoogleRealtimeModelSettings` currently constructs a `MultiSpeakerVoiceConfig` in `_speech_config()` that fails server-side during the WebSocket session instead of failing fast before dialing.

## Acceptance Criteria
1. Mark `MultiSpeaker` as `@deprecated(..., category=PydanticAIDeprecationWarning)`.
2. Remove `multi_speaker` / `MultiSpeakerVoiceConfig` handling from `_speech_config()` so it only configures `voice_config` (from `google_voice`) and `language_code` (from `google_language_code`).
3. Add a `_check_voice_settings(self, settings: GoogleRealtimeModelSettings) -> None` method on `GoogleRealtimeModel` (called before dialing) that raises `UserError` if `'google_multi_speaker' in settings`.
