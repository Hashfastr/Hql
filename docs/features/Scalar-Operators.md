# Scalar operators
These operators are used inside expressions, mostly in `where` predicates and in `project`/`extend` assignments.
Examples below use this table:

```
datatable (a:int, b:string) [1, "Hello World", 2, "foo-bar", 3, "HELLO"]
```

## Logical
| Operator | Meaning |
| --- | --- |
| `and` | both sides true |
| `or` | either side true |
| `not(expr)` | negation, see [not()](./Functions/Logic.md#not) |
| `( ... )` | grouping |

`and` binds tighter than `or`, so `a >= 2 and b has "hello" or a == 2` reads as `(a >= 2 and b has "hello") or a == 2`.

## Equality and comparison
| Operator | Meaning | Example |
| --- | --- | --- |
| `==` | equal, case sensitive for strings | `b == "HELLO"` → row 3 |
| `!=` | not equal | `b != "HELLO"` → rows 1, 2 |
| `=~` | equal, case insensitive | `b =~ "hello"` → row 3 |
| `!~` | not equal, case insensitive | `b !~ "hello"` → rows 1, 2 |
| `<`, `<=`, `>`, `>=` | ordering, numbers and datetimes | `a > 1` → rows 2, 3 |

A comparison whose sides are both literals is evaluated at compile time, e.g. `1 == 1` becomes `true`.

`<>` parses, but right now it behaves like `==` (workspace-z6s), so use `!=`.

## Set membership
| Operator | Meaning | Example |
| --- | --- | --- |
| `in (v, ...)` | equal to any value | `a in (1, 3)` → rows 1, 3 |
| `in~ (v, ...)` | `in`, case insensitive | `b in~ ("hello", "FOO-BAR")` → rows 2, 3 |
| `!in (v)` | not equal to the value | `a !in (1)` → rows 2, 3 |
| `!in~ (v)` | `!in`, case insensitive | `b !in~ ("hello")` → rows 1, 2 |

`!in` and `!in~` only work with a single value for now.
With several values they match every row (workspace-8it).

The list can contain the range returned by [ip4subnet()](./Functions/IP.md#ip4subnet) for IP range checks.

## Range
| Operator | Meaning | Example |
| --- | --- | --- |
| `between (start .. end)` | `start <= x <= end` | `a between (2 .. 3)` → rows 2, 3 |
| `!between (start .. end)` | outside the range | `a !between (2 .. 3)` → row 1 |

Works on numbers and datetimes, e.g. `t between (datetime(2024-01-01) .. datetime(2024-01-02))`.

## String matching
Every string operator is **case insensitive** unless it ends in `_cs`.
Prefixing one with `!` negates it, e.g. `!has`, `!contains_cs`, `!startswith`.

| Operator | Matches when the field... | Example |
| --- | --- | --- |
| `has`, `has_cs` | contains the value | `b has "hello"` → rows 1, 3 |
| `:` | same as `has` | `b : "world"` → row 1 |
| `contains`, `contains_cs` | contains the value | `b contains "o-b"` → row 2 |
| `startswith`, `startswith_cs` | starts with the value | `b startswith "hel"` → rows 1, 3 |
| `endswith`, `endswith_cs` | ends with the value | `b endswith "bar"` → row 2 |
| `hasprefix`, `hasprefix_cs` | same as `startswith` | `b hasprefix "hel"` → rows 1, 3 |
| `hassuffix`, `hassuffix_cs` | same as `endswith` | `b hassuffix "LD"` → row 1 |
| `has_any (v, ...)`, `has_any_cs` | contains any of the values | `b has_any ("world", "bar")` → rows 1, 2 |
| `has_all (v, ...)`, `has_all_cs` | contains all of the values | `b has_all ("hello", "world")` → row 1 |
| `matches regex "re"` | matches the regular expression (case sensitive) | `b matches regex "^[a-z]+-"` → row 2 |

Differences from Kusto:
- The `has` family isn't term based in Hql: `has` is a plain substring match, the same as `contains`.
  `hasprefix`/`hassuffix` match the start/end of the whole string, not of each term.
  (When a query is compiled to a database that does term matching, the database's own semantics apply.)
- `contains_any`/`contains_all` (and their `_cs` forms) parse, but are currently treated as `in`, i.e. exact equality (workspace-yqs).
  Use `has_any`/`has_all` instead.
- `like` and `notlike` aren't supported.
- To make a regex case insensitive, use an inline flag: `matches regex "(?i)^hello"`.
- String comparisons on nested paths (`o.q == "s"`, `o.q has "s"`) don't work yet (workspace-429).
  Numeric comparisons on nested paths do work (`o.p == 1`).

## Arithmetic
| Operator | Meaning |
| --- | --- |
| `+`, `-` | addition, subtraction |
| `*`, `/`, `%` | multiplication, division, modulo |
| `-x` | negation |

`*`, `/` and `%` bind tighter than `+` and `-`, and all of them are left associative.
`/` always produces a float.
Expressions with only literal operands are folded at compile time.

```
datatable (a:int, b:int) [7, 2]
| project add = a + b, sub = a - b, mul = a * b, div = a / b, mod = a % b, neg = -a, grp = (a + b) * 2

{
    "datatable": [{"add": 9, "sub": 5, "mul": 14, "div": 3.5, "mod": 1, "neg": -7, "grp": 18}]
}
```

## Literals
| Kind | Examples |
| --- | --- |
| integer (64 bit) | `1`, `-5` |
| real (64 bit) | `1.5` |
| boolean | `true`, `false` |
| string | `"x"`, `'x'` |
| verbatim string, no escapes | `@"C:\path"` |
| multi-line string | `"""..."""`, `'''...'''` |
| obfuscated string | `h"secret"` (same value, marked as obfuscated) |
| concatenated string | `"fo" "o-bar"` is `"foo-bar"` |
| datetime | `datetime(2024-01-01)`, `datetime(2024-01-01T12:00:00Z)` |
| timespan | `1h`, `30min`, `10s`, `1.5d`, `10ms`, `5micros` |

## Field references
| Syntax | Meaning |
| --- | --- |
| `name` | top level field |
| `a.b.c` | nested field |
| `['@timestamp']` | field whose name isn't a plain identifier |
