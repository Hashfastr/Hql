# Array (multivalue) functions

## len()
`len(x)` returns the number of elements in an array field, as a `ulong`.
Aliases: `array_length`.

An empty array gives `0`.
If the field isn't an array, or doesn't exist in a table, that table gets no value.

```
database('json').file('t.json')
| extend n = len(c)
| project a, n

// c values: [1, 2, 3], [4], []
{
    "t.json": [{"a": 1, "n": 3}, {"a": 2, "n": 1}, {"a": 3, "n": 0}]
}
```

## make_mv()
`make_mv(x, ...)` behaves differently depending on where it is used.
Aliases: `make_list`.

**Outside an aggregation** (`extend`, `project`) it builds one array per row out of the given fields.
The values are cast to a common type first.
Handy for "any direction" fields, e.g. `ips = make_mv(source.ip, destination.ip)`.

```
datatable (a:int, b:int) [1, 5, 2, 6]
| extend m = make_mv(a, b)

{
    "datatable": [{"m": [1, 5], "a": 1, "b": 5}, {"m": [2, 6], "a": 2, "b": 6}]
}
```

**Inside `summarize`** it collects the field's values for each group into an array, see [Aggregation](./Aggregation.md#make_list--make_mv).
