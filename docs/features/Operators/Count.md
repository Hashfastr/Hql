# count
The `count` operator counts the rows of each table.
By default it replaces every table with a single row using this schema:

```
{
    "Count": hqlt.long
}
```

If an earlier operator left no tables at all (e.g. a `where` on a field that no table has), `count` still returns a single table, `{"count": [{"Count": 0}]}`.

With an `as` clause the input tables are left alone and the counts go into a new table instead.
Kusto dropped this feature, Hql brings it back.
The new table has this schema, one row per input table:

```
{
    "Table": hqlt.string,
    "Count": hqlt.long
}
```

Kusto queries using this operator are compatible with Hql and return the same results.

```
// Replaces each table's contents with its count
datatable (a:int, b:string) [1, "x", 2, "y", 3, "z"]
| count

{
    "datatable": [{"Count": 3}]
}

// Leaves the tables intact and writes the counts into the counts table
database('json').file('t.json', 'u.json')
| project a
| count as counts

{
    "t.json": [{"a": 1}, {"a": 2}, {"a": 3}],
    "u.json": [{"a": 1}, {"a": 2}, {"a": 5}],
    "counts": [{"Table": "t.json", "Count": 3}, {"Table": "u.json", "Count": 3}]
}
```

`count` the operator is not the same thing as `count()` the aggregation function used inside [summarize](./Summarize.md).
