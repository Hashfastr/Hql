# Functions
Functions are called as `name(args)`.
Source functions can also be chained, as in `database('x').index('y')`.

| Function | Aliases | Summary |
| --- | --- | --- |
| **[Casting](./Functions/Casting.md)** | | |
| `toint(x)` | | cast to `int` |
| `tofloat(x)` | | cast to `double` |
| `todouble(x)` | | cast to `double` |
| `tostring(x)` | | cast to `string` |
| `toip4(x)` | | cast an IPv4 string to `ip4` |
| `todatetime(x)` | | cast to `datetime` |
| **[String](./Functions/String.md)** | | |
| `tolower(x)` | | lowercase |
| `base64(s [, encoding])` | `b64` | Base64 encode |
| `base64dec(s [, encoding])` | `b64dec` | Base64 decode |
| `base64offset(s [, encoding])` | `base64off`, `b64off` | Base64 forms of `s` at all 3 byte offsets |
| `wide(s)` | | UTF-16LE bytes of `s` |
| **[Arrays](./Functions/Arrays.md)** | | |
| `len(x)` | `array_length` | number of elements in an array |
| `make_mv(x, ...)` | `make_list` | build an array from fields (also an aggregation) |
| **[Time](./Functions/Time.md)** | | |
| `now()` | | current datetime |
| `ago(timespan)` | | current datetime minus a timespan |
| **[IP](./Functions/IP.md)** | | |
| `ip4subnet(cidr)` | | IPv4 address range of a CIDR block |
| **[Logic](./Functions/Logic.md)** | | |
| `isnull(field)` | | field is null |
| `isnotempty(x, ...)` | | every argument is non-null and not `""` |
| `not(expr)` | | negation |
| **[Aggregation](./Functions/Aggregation.md)** | | |
| `count()` | | rows per group |
| `make_list(x, ...)` | `make_mv` | array of values per group |
| **[Statistics](./Functions/Statistics.md)** | | |
| `series_stats(x [, ignore_nonfinite])` | | min/max/avg/stdev/variance of a field |
| **[Sources](./Functions/Sources.md)** | | |
| `database(name)` | | select a configured database |
| `index(pattern)` | | select an index on the database |
| `file(name, ...)` | | select local files on the database |
| `http(url, ...)` | | select remote files on the database |
| `raw(query)` | | run a native query on the database |
| `macro(name, ...)` | | expand a macro defined in the database config |
| `product(pattern, ...)` | | select configured products (HaC) |
| `category(pattern, ...)` | | select configured categories (HaC) |
| `service(pattern, ...)` | | select configured services (HaC) |
| **[Output](./Functions/Output.md)** | | |
| `scot4(...)` | | publish detection results to a SCOT 4 server |

Function names are case sensitive.
An unknown function name fails at compile time.

`bincount()` is registered but does nothing yet (it returns empty data), so it isn't documented.
