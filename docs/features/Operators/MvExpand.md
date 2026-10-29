# mv-expand
The `mv-expand` operator turns an array (multivalue) field into one row per element.
The other fields are copied onto each new row.
`mvexpand` is an alias.

The syntax is `mv-expand field [to type], ... [limit N]`.

- An empty or null array gives a single row with a null value.
- `to type` casts the expanded values, e.g. `to string`.
- `limit N` keeps at most N elements from each array.
- Nested paths are expanded in place, so the surrounding object is kept.
- Fields that aren't arrays, or that don't exist in a table, are skipped.

```
// t.json c values: [1, 2, 3], [4], []
database('json').file('t.json')
| project a, c
| mv-expand c

{
    "t.json": [
        {"a": 1, "c": 1}, {"a": 1, "c": 2}, {"a": 1, "c": 3},
        {"a": 2, "c": 4},
        {"a": 3, "c": null}
    ]
}

database('json').file('t.json')
| project a, c
| mv-expand c to string limit 2

{
    "t.json": [{"a": 1, "c": "1"}, {"a": 1, "c": "2"}, {"a": 2, "c": "4"}, {"a": 3, "c": null}]
}
```

Expanding several fields in one `mv-expand` currently gives their cross product.
Kusto pairs the elements by position instead (workspace-i7d).
