# sort
The `sort` operator orders the rows of each table.
`order` is an alias, and the syntax is `sort by expr [asc | desc] [nulls first | nulls last], ...`.

- The default direction is `desc`, the same as Kusto.
- Nulls default to `nulls last` for `desc` and `nulls first` for `asc`.
- With several sort keys, later keys break ties left by earlier ones.

```
datatable (a:int, b:string) [1, "x", 3, "y", 2, "z"]
| sort by a

{
    "datatable": [{"a": 3, "b": "y"}, {"a": 2, "b": "z"}, {"a": 1, "b": "x"}]
}

datatable (a:int, b:string) [1, "x", 3, "y", 2, "z"]
| order by a asc

{
    "datatable": [{"a": 1, "b": "x"}, {"a": 2, "b": "z"}, {"a": 3, "b": "y"}]
}

// Several keys, nested fields, explicit null placement
Database
| sort by o.p asc nulls last, b desc
```
