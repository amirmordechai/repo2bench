# Task: Exclude DML CTE aliases from SQL dependencies in `find_sql_refs`

## Problem Description
In `marimo/_ast/sql_visitor.py`, `find_sql_refs(sql_statement)` misidentifies CTE aliases in DML queries (e.g., `WITH changed AS (INSERT INTO items VALUES (1) RETURNING *) SELECT * FROM changed`) or nested subquery CTEs as external table dependencies because:
1. `build_scope(expression)` exposes DML CTE references as plain `exp.Table` sources.
2. `_collect_table_refs_excluding_ctes` only checks top-level `WITH` clauses and fails to distinguish the target table of an `INSERT`/`UPDATE`/`DELETE` from a CTE reference of the same name, or recursive vs non-recursive CTE self-references.

## Requirements
1. In `marimo/_ast/sql_visitor.py`, inside `find_sql_refs`, implement `is_cte_reference(table: exp.Table) -> bool` that:
   - Returns `False` if `table.db or table.catalog`, or if `table` (or its parent `exp.Schema`) is the direct target (`parent.this is target`) of an `exp.Insert`, `exp.Update`, or `exp.Delete`.
   - Walks ancestor `parent` nodes checking `with_clause` (`parent` if `isinstance(parent, exp.With)` else `parent.args.get("with_")`), and for `cte in with_clause.expressions`: if `cte is node and not with_clause.args.get("recursive")` breaks (since non-recursive CTEs cannot reference themselves or later CTEs), if `cte.alias.lower() == table_name` returns `True`, and if `cte is node` breaks.
2. Use `not is_cte_reference(table)` in `_collect_table_refs_excluding_ctes` AND skip `source` in the `build_scope` traversal when `requires_table_scan and is_cte_reference(source)`.
