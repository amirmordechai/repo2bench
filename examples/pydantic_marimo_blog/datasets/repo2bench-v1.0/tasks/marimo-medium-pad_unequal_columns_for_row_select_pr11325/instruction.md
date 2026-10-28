# Task: Pad unequal columns with `None` for row selection, cell selection, and search in `DefaultTableManager`

## Problem Description
In `marimo/_plugins/ui/_impl/tables/default_table.py`, when `DefaultTableManager` holds column-oriented dictionary data where columns have different lengths (e.g. `{"a": [2], "b": [10, 20]}`), `sort_values` pads shorter columns with `None` up to `self.get_num_rows()`, but `select_rows`, `select_cells`, and `search` index directly into `self.data[key][row]`, raising `IndexError: list index out of range`!

## Requirements
1. Add a helper method `_padded_columns(self) -> dict[str, Sequence[Any]]` on `DefaultTableManager` in `marimo/_plugins/ui/_impl/tables/default_table.py` that pads any column shorter than `self.get_num_rows()` with `None` (`list(values) + [None] * (num_rows - len(values))`).
2. Use `self._padded_columns()` in `select_rows`, `select_cells`, `search`, and `sort_values` when `self.is_column_oriented` is true so shorter columns are padded with `None` without mutating `self.data`.
