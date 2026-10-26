# Goal: Accept unrounded float probabilities and scores from `SystemOneModel` backends such as vLLM

## Context & Goal
`SystemOneModel` validates that returned `ChoiceAnswer` and `ScoreAnswer` probabilities and expected scores match within display-rounding intervals (`_probability_bounds` and `_score_fits`). While the hosted Jev backend rounds probabilities to 2 decimal places, self-hosted backends like vLLM return unrounded float32/float64 softmax probabilities with many decimal digits. Because `_probability_bounds` and `_score_fits` compute half-unit intervals from the number of printed decimal places, unrounded floats get an interval narrower than float32 arithmetic error (`~1e-7`), causing valid vLLM responses to fail with `UnexpectedModelBehavior`.

## Acceptance Criteria
1. Define `_FLOAT_TOLERANCE = Decimal('1e-6')` in the SystemOne model module and accept a `float_tolerance: Decimal = Decimal(0)` keyword argument in `_probability_bounds` and `_score_fits` in the decision model module.
2. Ensure each probability and score half-unit interval in `_probability_bounds` and `_score_fits` is at least `float_tolerance` wide (`max(..., float_tolerance)`), and pass `float_tolerance=_FLOAT_TOLERANCE` from `SystemOneModel`.
