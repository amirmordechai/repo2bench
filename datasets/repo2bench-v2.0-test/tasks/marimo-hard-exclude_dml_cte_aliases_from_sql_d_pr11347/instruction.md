# Goal: Exclude DML CTE aliases and respect CTE scope rules in `find_sql_refs`

## Context & Goal
`find_sql_refs(sql_statement)` currently misidentifies CTE aliases in DML queries (such as `WITH changed AS (INSERT INTO items VALUES (1) RETURNING *) SELECT * FROM changed`) or nested subquery CTEs as external table dependencies because `build_scope` exposes DML CTEs as plain `exp.Table` sources and `_collect_table_refs_excluding_ctes` only checks top-level `WITH` clauses.

## Acceptance Criteria
1. Inside `find_sql_refs`, implement `is_cte_reference(table: exp.Table) -> bool` that returns `False` for qualified tables (`table.db or table.catalog`) or direct targets of `exp.Insert, exp.Update, exp.Delete`, and walks ancestor `with_` clauses respecting `with_clause.args.get("recursive")` and `cte.alias.lower() == table_name`.
2. Filter with `not is_cte_reference(table)` in `_collect_table_refs_excluding_ctes` and skip `source` during `build_scope` traversal when `requires_table_scan and is_cte_reference(source)`.
