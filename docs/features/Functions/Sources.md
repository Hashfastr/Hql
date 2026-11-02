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
They are used for Hql-as-Code (HaC) detections and Sigma logsources.
They resolve against the classes in scope when the query compiles: a product is a class, and services and categories are its members.

```
class windows = {
    let process_creation = database('elastic').index('so-beats-*')
    | where EventID == 1
    ;
};
product('windows').category('process_creation')
| where CommandLine has "powershell"
```

The selection is walked as a nested class path in the order `product.service.category`, skipping any part that isn't given:

| Selection | Resolves to |
| --- | --- |
| `product('windows').category('process_creation')` | `windows.process_creation` |
| `product('windows').service('security')` | `windows.security` |
| `product('windows').service('sysmon').category('process_creation')` | `windows.sysmon.process_creation` |
| `product('windows')` | every tabular member of `windows` |
| `category('process_creation')` | `process_creation` in every class, or a top-level `let process_creation` if no class has it |

- Every argument is a glob pattern, and several arguments or calls at the same level are combined.
- When a selection ends on a class rather than a let, all of that class's tabular members are used. Members starting with `_` (helpers like `_base`) are skipped.
- When several members match, the results are combined as separate upstream sources.

If nothing resolves, the query fails with `No source resolved for <path>`, e.g. `No source resolved for windows.process_creation`.

### Sigma header
Sigma rules carry no Hql of their own, so the classes their logsource resolves against are brought in by a header in the config.
The header is Hql with only declarations (imports, classes, lets, maps), and it is prepended to every Sigma rule:

```yaml
sigma:
  header: |
    import newmaps.windows
```

Imports are resolved against the config directory.
