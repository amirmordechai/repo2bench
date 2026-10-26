# Goal: Pad unequal-length dictionary columns with `None` across `select_rows`, `select_cells`, and `search` in `DefaultTableManager`

## Context & Goal
When `DefaultTableManager` wraps column-oriented dictionary data where columns have unequal lengths (e.g. `{"a": [2], "b": [10, 20]}`), `sort_values` pads shorter columns with `None` up to `self.get_num_rows()`, but `select_rows`, `select_cells`, and `search` index directly into `self.data[key][row]` and crash with `IndexError: list index out of range`.

## Acceptance Criteria
- Add a `_padded_columns(self)` helper on `DefaultTableManager` that pads any column shorter than `self.get_num_rows()` with `[None] * (num_rows - len(values))` without mutating `self.data`, and use `self._padded_columns()` in `select_rows`, `select_cells`, `search`, and `sort_values`.
