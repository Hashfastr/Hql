# DEATHCon 2026 demo

A marimo notebook in six sections. The first five run offline against fake JSON databases:

1. **Raw compile**: a Sigma rule compiled to Lucene, Elastic DSL, KQL and SPL with no config or database.
2. **Sigma source config**: one Sigma header maps `logsource` to Elastic (process creation) and Splunk (security log), with field mapping.
3. **Direct querying**: run Sigma rules and Hql against those sources.
4. **HaC**: Hql as Code, Sigma converted and then extended past what Sigma can express (thresholds, cross-database joins).
5. **HaC engine, static dataset**: a button starts the HaC engine over `hac/` and its web UI on http://localhost:8080.
6. **HaC engine, Log Analytics**: a button starts the engine over `hac-loganalytics/` against your workspace, web UI on http://localhost:8081. Needs a Workspace ID in `config/loganalytics.yml` and an `az login`.

## Layout

```
deathcon-26/
├── deathcon.py              # the notebook
├── config/                  # pass to Config() / -c
│   ├── sigma.yml            # sigma header: import maps.sources
│   ├── fake.yml             # fake-elastic, fake-splunk (JSON databases over data/)
│   ├── elastic.yml          # live Elasticsearch placeholder
│   ├── splunk.yml           # live Splunk placeholder
│   ├── kusto.yml            # live Azure Data Explorer placeholder
│   ├── loganalytics.yml     # live Log Analytics / Sentinel workspace placeholder
│   └── maps/
│       ├── fields.hql       # Sigma field names -> ECS / Splunk TA fields
│       ├── fake.hql         # class windows -> fake databases
│       ├── live.hql         # class windows -> elastic / splunk
│       └── sources.hql      # picks fake or live
├── data/
│   ├── windows-process.ndjson   # ECS process events (Elastic stand-in)
│   └── windows-security.ndjson  # 4769 events (Splunk stand-in)
├── rules/                   # unmodified SigmaHQ rules
├── hac/
│   ├── kerberoasting.hql               # straight Sigma conversion
│   ├── kerberoasting_threshold.hql     # adds the threshold the Sigma rule asks for
│   └── powershell_then_kerberoast.hql  # Elastic + Splunk join on client IP
├── hac-loganalytics/        # HaC over maps.azure, for a Log Analytics workspace
│   ├── azurehound_signin.hql           # AzureHound user agent in SigninLogs
│   └── password_spray.hql              # many failed sign-ins from one IP
└── ctf/                     # Sigma hunting CTF on the TF11 datasets, see ctf/README.md
```

`config/sigma.yml` points raw Sigma at the TF11 datasets (`maps/tf11.hql`, field maps in `maps/tf11_fields.hql`). The notebook sets its own header, so it stays on the offline fake data.

`maps/azure.hql` does the same for Azure Monitor and Sentinel tables, field maps in `maps/azure_fields.hql`. The tables can be queried in an Azure Data Explorer cluster or a Log Analytics workspace. To use them:

1. Fill in `config/loganalytics.yml` for a Log Analytics workspace (Sentinel's tables live here), or `config/kusto.yml` for Azure Data Explorer. The workspace needs its Workspace ID from the Overview blade. It authenticates as whoever ran `az login`, who needs Log Analytics Reader; set `auth: secret` to use an app registration instead.
2. Set `let azure_db` at the top of `maps/azure_fields.hql` to `'kusto'` or `'loganalytics'` to match. The notebook's Log Analytics engine runs on a copy of `config/` with it set to `'loganalytics'`, so it doesn't need this.
3. Set the header in `config/sigma.yml` to `import maps.azure`.

Either database also works without the maps, e.g. `database('loganalytics').raw('SecurityEvent | where TimeGenerated > ago(1h)') | where EventID == 4769`. Under HaC, a Log Analytics query is also bounded server side by the run's time window.

## Running

Notebook:

```bash
uv sync --group notebooks
uv run marimo edit examples/deathcon-26/deathcon.py
```

CLI, from the repo root (`local-base` in `config/fake.yml` is relative to the CWD):

```bash
uv run python -m Hql -c examples/deathcon-26/config -f examples/deathcon-26/hac/kerberoasting_threshold.hql
```

A raw Sigma rule on the CLI now runs against TF11, and integer values such as `EventID: 4769` fail against its string fields. To run the workshop's rules against the fake data, use the notebook.

Add `-nx` to compile only, or `-dpar` to print the deparsed Hql.

HaC engine and web UI, same as the notebook's last cell (needs free-threaded Python `3.14t` and a built `Hql-Interface/dist`):

```bash
uv run python -m Hql -eng -d examples/deathcon-26/hac -c examples/deathcon-26/config
```

The engine writes `<run_id>.log` files into `hac/` while detections run; they're gitignored.

## Going live

- Fill in `config/splunk.yml` (and `config/elastic.yml` if you have one). Config doesn't read env vars, so don't commit secrets; `git update-index --skip-worktree <file>` keeps local edits out of git.
- Change `config/maps/sources.hql` to `import maps.live;`. To go live with only Splunk, change just the `security` line in `config/maps/fake.hql`.
- Caveats:
  - In live mode the HaC time bound only applies to the first source compiled (bug workspace-vuc).
  - Elastic `host.ip` is an array and Splunk `Client_Address` may be `::ffff:`-prefixed, so the join in `powershell_then_kerberoast.hql` may need normalising.

## Attribution

The files in `rules/` are unmodified SigmaHQ rules under the [Detection Rule License 1.1](https://github.com/SigmaHQ/Detection-Rule-License); authors are credited in each rule. The HaC files are derived works and keep the original authors, links and license.
