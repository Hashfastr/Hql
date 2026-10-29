# top
The `top` operator sorts each table by one expression and keeps the first N rows.
The syntax is `top N by expr [asc | desc] [nulls first | nulls last]`.
It is the same as `sort by ... | take N`, and all the other fields are kept.

The direction defaults to `desc`, so plain `top` gives the largest values.
N has to be a non-negative integer.

```
datatable (a:int, b:string) [1, "x", 3, "y", 2, "z"]
| top 2 by a

{
    "datatable": [{"a": 3, "b": "y"}, {"a": 2, "b": "z"}]
}

datatable (a:int, b:string) [1, "x", 3, "y", 2, "z"]
| top 2 by a asc

{
    "datatable": [{"a": 1, "b": "x"}, {"a": 2, "b": "z"}]
}
```
