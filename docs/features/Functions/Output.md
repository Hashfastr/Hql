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

## discord()
`discord(...)` posts results to a Discord channel as a table alert, through a bot.
Each table with rows becomes one message: an embed with the HaC title, level colour, description, detection id, and the rows as a fixed-width table in a code block.
Without HaC metadata the title is `Hql alert: <table name>`.
Empty tables aren't posted.

It returns one row per table with `table`, `server`, `channel`, `rows`, `status` and `message_id`.

Arguments are optional named parameters:

| Parameter | Default (from the `discord` function config) | Meaning |
| --- | --- | --- |
| `server = "name"` | `default_server` | Discord server (guild) name, or its ID |
| `channel = "name"` | `default_channel` | text channel name (a leading `#` is fine), or its ID |

Names are looked up through the bot's servers and channels; IDs are used as is.
An unknown server or channel fails the query, and so does a failed post.

Function config:

```yaml
function:
  name: discord
  conf:
    token: '<bot token>'   # empty or missing: skip posting, status says so
    default_server: DEATHCon
    default_channel: alerts
    row_limit: 10          # rows shown per alert, default 10
```

The bot needs View Channel and Send Messages in the channel.
Rows that don't fit in Discord's 4096-character embed description are dropped, and the footer says how many are shown.

```
Detection
| project alert = discord()

Detection
| project alert = discord(server = "DEATHCon", channel = "#alerts")
| unnest alert   // the status as plain columns
```
