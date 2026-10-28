# Task: Keep `bool` and `int` inputs on separate `Literal` decision branches in `pydantic_graph`

## Problem Description
In Python, `isinstance(True, int)` is `True` and `True == 1` (`False == 0`). In `pydantic_graph/pydantic_graph/graph_builder.py`, inside `_GraphIterator` when matching a decision branch whose `branch_source` origin is `Literal`:
`inputs_match = inputs in get_args(branch_source)`
matches `inputs = 1` against `Literal[True]` and `inputs = True` against `Literal[1]`.

## Requirements
1. In `pydantic_graph/pydantic_graph/graph_builder.py`, when `get_origin(branch_source) is Literal`:
   - Extract `literal_values = get_args(branch_source)`.
   - If `isinstance(inputs, int)`, filter `literal_values` so that `int`/`bool` literal members only match when `isinstance(v, bool) == isinstance(inputs, bool)` (while non-bool `int` values like `IntEnum` members still match `int` literals).
   - Then check `inputs_match = inputs in literal_values`.
