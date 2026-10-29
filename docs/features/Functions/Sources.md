# Source functions
Source functions choose where a query reads its data from.
They're chained with `.`, starting from a database:

```
database('elastic').index('so-beats-*')
| where ...
```

If a chain doesn't start with `database(...)`, the configured default database is used.
For example, `file('t.json')` is short for `database(<default>).file('t.json')`.

Which functions a database type supports:

| Database type | `index` | `file` | `http` | `raw` | `macro` |
| --- | --- | --- | --- | --- | --- |
| Elasticsearch | ✓ | | | | ✓ |
| Opensearch | ✓ | | | | ✓ |
| Splunk | ✓ | | | | ✓ |
| SQLite | ✓ | | | | ✓ |
| SCOT | ✓ | | | | ✓ |
| JSON | | ✓ | ✓ | | ✓ |
| CSV | | ✓ | ✓ | | ✓ |
| Kusto | | | | ✓ | |

## database()
`database(name)` selects a database defined in the config.
The name can be a string or a `let` variable.

When the database config contains a `preamble` (an `hql:` pipeline), that pipeline is applied to everything read from the database.
An unknown name, or a config without a `type`, fails the query.

## index()
`index(pattern)` selects the index (or table/source, depending on the database) to read.
Wildcards are passed through to the database, and each matched index becomes its own table in Hql.

```
database('elastic').index('so-beats-2022.10.*')
```

## file()
`file(name, ...)` reads one or more local files.
The paths are relative to the database's `local-base` directory, and each file becomes a table named after the file.

```
database('json').file('t.json', 'u.json')
```

## http()
`http(url, ...)` reads one or more files over HTTP.
The URLs are relative to the database's `http-base`, and each one becomes a table.

```
database('json').http('tf11-so-network.json')
```

## raw()
`raw(query)` sends a query string in the database's native language, unchanged.
Only Kusto supports it right now.

```
database('kusto').raw('StormEvents | take 10')
```

## macro()
`macro(name, ...)` expands macros defined under `macro:` in the database config.
Each macro is a named Hql snippet.
With several names, the results are combined as separate upstream sources.

```yaml
# Database config
macro:
  network:
    hql: |
      database('json').http('tf11-so-network.json')
```

```
database('json').macro('network')
| take 10
```

## product(), category(), service()
These select data sources by **what they are** rather than by where they live.
They are used for Hql-as-Code (HaC) detections.
They resolve against the `products` and `categories` sections of the config: each product lists upstream Hql source queries, and those can be narrowed down further by category and service.

- `product(pattern, ...)` selects the products whose names match the glob patterns.
- `category(pattern, ...)` narrows the selection to matching categories.
  Used on its own, it starts from every product (`*`).
  When no product category matches, it falls back to a standalone category defined in the config.
- `service(pattern, ...)` narrows the selection to matching services.
  Used on its own, it starts from every product.

```
product('windows').category('process_creation')
| where CommandLine has "powershell"
```

If nothing resolves, the query fails with `No sources resolved from product/category/service config`.
