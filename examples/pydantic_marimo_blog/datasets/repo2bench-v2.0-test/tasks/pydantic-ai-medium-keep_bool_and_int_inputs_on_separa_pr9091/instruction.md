# Goal: Prevent `bool` and `int` inputs from matching each other's `Literal` decision branches in `pydantic_graph`

## Context & Goal
In Python, `bool` is a subclass of `int` (`True == 1` and `False == 0`). When a graph decision node routes inputs across branches typed with `Literal[1]` vs. `Literal[True]` (or `Literal[0]` vs. `Literal[False]`), checking `inputs in get_args(branch_source)` routes `True` into `Literal[1]` and `1` into `Literal[True]`.

## Acceptance Criteria
- When matching a `Literal` decision branch in the graph builder (`elif get_origin(branch_source) is Literal:`), ensure `bool` inputs do not match non-bool `int` literal arguments and non-bool `int` inputs (including `IntEnum` values) do not match `bool` literal arguments.
