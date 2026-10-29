# Casting functions
These functions cast a value to an Hql type.
See [TYPING](../../TYPING.md) for how each type is stored, e.g. an Hql `int` is a Polars `Int32`.

All of them take exactly one argument, either a field or a literal.
A value that can't be converted becomes `null`, it doesn't fail the query.
Casting a literal is done at compile time.

```
Dataset
| project int_as_str, int = toint(int_as_str)

// Pseudo
[
    {"int_as_str": "10", "int": 10},
    {"int_as_str": "15", "int": 15},
    {"int_as_str": "nope", "int": null},
]
```

## toint()
Converts to an Hql `int` (32 bit signed).

```
Database
| extend n = toint("5")       // 5 on every row
```

## tofloat()
Converts to an Hql `double` (64 bit).
Like Kusto, `tofloat` is the same as `todouble`/`toreal`.

## todouble()
Converts to an Hql `double` (64 bit).

```
Database
| extend f = tofloat(a), d = todouble("1.5")   // a = 1 → f = 1.0, d = 1.5
```

## tostring()
Converts to an Hql `string`.

```
Database
| extend s = tostring(a)      // a = 1 → s = "1"
```

## toip4()
Converts an IPv4 string into an Hql `ip4`.
It is stored as a `UInt32`, which makes range checks cheap, and is shown as a dotted string again when displayed.

```
database('json').file('t.json')
| extend i = toip4(ip)
| where i in (ip4subnet("10.0.0.0/8"))
| project ip

{
    "t.json": [{"ip": "10.1.2.3"}]
}
```

## todatetime()
Converts an ISO 8601 string into an Hql `datetime`.

```
Database
| extend t = todatetime(ts)   // "2024-01-01T00:00:00Z" → 2024-01-01T00:00:00
| where t > ago(7d)
```

Calling a cast on a field directly inside a `where` predicate doesn't work yet (workspace-99v).
`extend` the value first, as in the examples above.
