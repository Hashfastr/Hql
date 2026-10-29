# union
The `union` operator merges tables that are already in the pipeline into one table.
The syntax is `union pattern, ... [as name]`.

Every table whose name matches one of the patterns is concatenated, row by row, into a single table.
Fields missing from some tables come out as null.
Tables that don't match pass through unchanged.
If nothing matches, the data passes through untouched.

The merged table is named after the `as` clause.
Without `as`, it takes the name of the first matched table.

This differs from Kusto: Hql's `union` combines tables *already in the pipeline*.
It doesn't pull in new sources, so to union several sources, select them in the source function (e.g. `file('a.json', 'b.json')`).

```
database('json').file('t.json', 'u.json')
| project a
| union * as both

{
    "both": [{"a": 1}, {"a": 2}, {"a": 3}, {"a": 1}, {"a": 2}, {"a": 5}]
}

// Names with dots need brackets
database('json').file('t.json', 'u.json')
| union ['t.json'], ['u.json'] as both
```
