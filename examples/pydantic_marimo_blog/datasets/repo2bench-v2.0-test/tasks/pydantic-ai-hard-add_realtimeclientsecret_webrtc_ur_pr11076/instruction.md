# Goal: Include `webrtc_url` on `RealtimeClientSecret` for OpenAI and Azure OpenAI WebRTC sessions

## Context & Goal
When a browser client uses an ephemeral `RealtimeClientSecret` minted by `OpenAIRealtimeModel`, it needs to know the endpoint URL where it should POST its WebRTC SDP offer (which differs between OpenAI and Azure OpenAI, and is `None` if the model profile does not support WebRTC).

## Acceptance Criteria
- Expose `webrtc_url: str | None = None` on `RealtimeClientSecret` and populate it during client secret minting when the model profile supports WebRTC.
