# datatable
The `datatable` operator creates an inline table from literal values.
It's a source, so it starts a pipeline.

The syntax is `datatable (column:type, ...) [value, value, ...] [as name]`.

Values are listed row by row, filling the columns left to right.
The number of values has to be a multiple of the number of columns.
The table is named `datatable` unless `as` gives it a name.

Column types are Hql types, see [TYPING](../../TYPING.md).
Types tested here include `int`, `long`, `real`, `string`, `bool`, `datetime` and `timespan`.

```
datatable (a:int, b:string) [1, "x", 2, "y", 3, "z"]

{
    "datatable": [{"a": 1, "b": "x"}, {"a": 2, "b": "y"}, {"a": 3, "b": "z"}]
}

datatable (a:int, s:string, f:real, b:bool, d:datetime, t:timespan) [1, "x", 1.5, true, datetime(2024-01-01), 1h] as t
```

`dynamic(...)` values (arrays and objects) aren't accepted yet (workspace-isv).
