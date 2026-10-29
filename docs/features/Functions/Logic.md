# Logic functions
These functions build predicates for `where`.

## isnull()
`isnull(field)` is true when the field is null.
The argument has to be a field reference.

```
// n.json: {"a": 1, "b": null}, {"a": 2, "b": "y"}
database('json').file('n.json')
| where isnull(b)

{
    "n.json": [{"a": 1, "b": null}]
}
```

## isnotempty()
`isnotempty(x, ...)` is true when **every** argument is non-null.
For string fields, the value also has to be something other than `""`.
It takes one or more arguments.

```
// b values: "x", "y", ""
database('json').file('t.json')
| where isnotempty(b)
| project a

{
    "t.json": [{"a": 1}, {"a": 2}]
}
```

## not()
`not(expr)` negates a predicate or a logic function.

```
Database
| where not(a == 2)

Database
| where not(isnull(b))
```
