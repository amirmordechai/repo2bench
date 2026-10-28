# Goal: Avoid division by zero when normalizing silent audio arrays in `mo.audio`

## Context & Goal
When a user passes an all-zero (silent) NumPy array to `mo.audio(np.zeros(8), rate=44100)` with normalization enabled (`normalize=True`), WAV conversion computes `max_abs_value = np.max(np.abs(data))`, which is `0.0`, and divides the audio samples by that zero peak amplitude. This emits runtime invalid-division / invalid-cast warnings and raises `FloatingPointError` under `np.errstate(invalid="raise")`.

## Acceptance Criteria
- When normalizing audio data to WAV, if `max_abs_value` is `0` (or not strictly positive), use a normalization divisor of `1` so silent mono or stereo arrays remain zero without dividing by zero.
