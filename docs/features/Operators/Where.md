# where
The `where` operator keeps only the rows that match a predicate.
`filter` is an alias.

The predicate can use any of the [scalar operators](../Scalar-Operators.md): comparisons, string matching, `in`, `between`, `and`/`or`, plus logic functions like `isnull()`, `isnotempty()` and `not()`.
When several `where` operators follow each other, Hql merges them into a single `and`.
When the source is a database, the predicate is pushed down to it wherever possible.

A table that doesn't have a referenced field is **dropped** from the results, it doesn't produce an error.

```
datatable (a:int, b:string) [1, "x", 2, "y", 3, "z"]
| where a > 1

{
    "datatable": [{"a": 2, "b": "y"}, {"a": 3, "b": "z"}]
}

// Combining conditions
Database
| where a >= 2 and b has "hello" or a == 2

// Let variables can be used as values
let x = 2;
Database
| where a == x
```

## Limitations
- Scalar functions applied to a field inside the predicate fail, e.g. `where todatetime(ts) > ago(1d)` (workspace-99v).
  `extend` the value first, then filter it: `| extend t = todatetime(ts) | where t > ago(1d)`.
- `where * has "x"` (search every column) parses but doesn't run (workspace-49p).
