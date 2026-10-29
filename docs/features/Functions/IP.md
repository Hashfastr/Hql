# IP functions

## ip4subnet()
`ip4subnet(cidr)` turns an IPv4 CIDR string into the numeric address range it covers.
For example, `"10.0.0.0/8"` gives `167772160 .. 184549375`.
The range is computed at compile time, and the argument can be a `let` variable.
An invalid CIDR fails the query.

Use it with `in` against an `ip4` field, so the comparison is numeric:

```
database('json').file('t.json')
| extend i = toip4(ip)
| where i in (ip4subnet("10.0.0.0/8"))
| project ip

{
    "t.json": [{"ip": "10.1.2.3"}]
}
```

The field has to be an `ip4`.
Comparing the range with a string field fails with a type error.
Cast the field with [toip4()](./Casting.md#toip4) first, or make sure the source maps it as `ip4`.
