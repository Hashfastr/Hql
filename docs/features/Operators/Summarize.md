# summarize
The `summarize` operator aggregates the rows of each table.
The syntax is `summarize [name =] aggregation, ... [by field, ...]`.

- With `by`, you get one row per distinct combination of the `by` fields, in order of first appearance.
- Without `by`, the whole table is aggregated into a single row.
- An aggregation can be given a name with `name = aggregation`.
  Unnamed ones get a default name (`count_` for `count()`).
  Repeated default names get numeric suffixes: `count_`, `count_1`, ...
- `by` fields can be nested paths, and keep their nesting in the output.

Aggregation functions available today:

| Function | Result |
| --- | --- |
| [`count()`](../Functions/Aggregation.md#count) | number of rows in the group |
| [`make_list(field, ...)` / `make_mv(field, ...)`](../Functions/Aggregation.md#make_list--make_mv) | array of the field's values in the group |

```
datatable (a:int, b:string) [1, "x", 1, "y", 2, "z"]
| summarize count() by a

{
    "datatable": [{"a": 1, "count_": 2}, {"a": 2, "count_": 1}]
}

datatable (a:int, b:string) [1, "x", 1, "y", 2, "z"]
| summarize n = count(), bs = make_list(b) by a

{
    "datatable": [{"a": 1, "n": 2, "bs": ["x", "y"]}, {"a": 2, "n": 1, "bs": ["z"]}]
}

// No by clause: one row per table
datatable (a:int, b:string) [1, "x", 1, "y", 2, "z"]
| summarize count()

{
    "datatable": [{"count_": 3}]
}

// Nested group key
Database
| summarize count() by o.q      // [{"o": {"q": "s"}, "count_": 1}, ...]
```

Computed group keys such as Kusto's `by bin(timestamp, 5m)` aren't supported, `by` takes field references only.
