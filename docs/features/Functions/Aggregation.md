# Aggregation functions
These are used inside [summarize](../Operators/Summarize.md).

## count()
`count()` returns the number of rows in each group, as a `uint`.
It takes no arguments.
Without a name the column is called `count_`.

```
datatable (a:int, b:string) [1, "x", 1, "y", 2, "z"]
| summarize count() by a

{
    "datatable": [{"a": 1, "count_": 2}, {"a": 2, "count_": 1}]
}
```

To count all rows of a table without grouping, use either `summarize count()` or the [count operator](../Operators/Count.md).

## make_list / make_mv
`make_list(x, ...)` returns an array of the field's values in each group, in row order.
Aliases: `make_mv`.
Without a name, the column keeps the field's name.

```
datatable (a:int, b:string) [1, "x", 1, "y", 2, "z"]
| summarize bs = make_list(b) by a

{
    "datatable": [{"a": 1, "bs": ["x", "y"]}, {"a": 2, "bs": ["z"]}]
}
```

The arguments have to be scalar fields, collecting object fields isn't supported.
Outside `summarize`, `make_mv` builds per-row arrays instead, see [Arrays](./Arrays.md#make_mv).
