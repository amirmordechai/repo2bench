# Task: Add `RealtimeClientSecret.webrtc_url` for OpenAI and Azure OpenAI WebRTC calls

## Problem Description
When a browser uses an ephemeral `RealtimeClientSecret` token minted by `OpenAIRealtimeModel`, it needs to know the URL where it should POST its WebRTC SDP offer (which on Azure OpenAI includes `?webrtcfilter=on`, and on providers without WebRTC support is `None`).

## Requirements
1. In `pydantic_ai_slim/pydantic_ai/realtime/model.py`, add `webrtc_url: str | None = None` to the `RealtimeClientSecret` dataclass (after `expires_at`).
2. In `pydantic_ai_slim/pydantic_ai/realtime/_openai_webrtc.py`, add `webrtc_url: str | None` to `mint_client_secret(...)` and pass `webrtc_url=webrtc_url` when constructing `RealtimeClientSecret`.
3. In `pydantic_ai_slim/pydantic_ai/realtime/openai.py`, pass `webrtc_url=self._webrtc_calls_url() if self.profile.get('supports_webrtc') else None` to `mint_client_secret(...)`.
