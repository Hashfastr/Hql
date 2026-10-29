# Output functions

## scot4()
`scot4(...)` publishes detection results to a SCOT 4 server as an alert group.
It's meant to run from the HaC engine: it only does something when the query is a HaC detection and has results.
Otherwise it returns empty data.

Arguments are optional named parameters:

| Parameter | Default (from the `scot4` function config) | Meaning |
| --- | --- | --- |
| `server = "name"` | `default` | which entry in `servers` to post to |
| `union = true/false` | `union` (or the older `always_union`), else `false` | whether to post all tables as one alert group |

Other function config keys: `servers` (list with a `name` each), `row_limit` (default 100), `verify_tls` (default `true`), and `source_tags` (`link_transform`, `blacklist`).

```
Detection
| project scot_res = scot4()

Detection
| project scot_res = scot4(server = "prod", union = true)
```

Before posting, it updates the detection's HaC metadata on the server.
