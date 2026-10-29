# Time functions
Both functions are evaluated once, at compile time.
Every row therefore gets the same value.

## now()
`now()` returns the current local datetime.
It takes no arguments.

```
Database
| extend n = now()
```

## ago()
`ago(timespan)` returns the current datetime minus the timespan.
The argument can be a timespan literal (`1h`) or a string containing one (`"1h"`).

Timespan units: `d`/`day(s)`, `h`/`hr(s)`/`hour(s)`, `m`/`min(s)`/`minute(s)`, `s`/`sec(s)`/`second(s)`, `ms`/`milli(s)`, `micro(s)`.
Fractions are allowed, e.g. `1.5d`.

```
Database
| extend t = todatetime(ts)
| where t > ago(1d)
```

Compare `ago()` with a datetime field that already exists, or with one created by `extend` first.
Wrapping the field in a function inside the `where` itself (`where todatetime(ts) > ago(1d)`) doesn't work yet (workspace-99v).
