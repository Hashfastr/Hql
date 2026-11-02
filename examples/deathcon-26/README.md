# DEATHCon 2026 demo

A marimo notebook in four sections, all running offline against fake JSON databases:

1. **Raw compile**: a Sigma rule compiled to Lucene, Elastic DSL, KQL and SPL with no config or database.
2. **Sigma source config**: one Sigma header maps `logsource` to Elastic (process creation) and Splunk (security log), with field mapping.
3. **Direct querying**: run Sigma rules and Hql against those sources.
4. **HaC**: Hql as Code, Sigma converted and then extended past what Sigma can express (thresholds, cross-database joins).

## Layout

```
deathcon-26/
├── deathcon.py              # the notebook
├── config/                  # pass to Config() / -c
│   ├── sigma.yml            # sigma header: import maps.sources
│   ├── fake.yml             # fake-elastic, fake-splunk (JSON databases over data/)
│   ├── elastic.yml          # live Elasticsearch placeholder
│   ├── splunk.yml           # live Splunk placeholder
│   └── maps/
│       ├── fields.hql       # Sigma field names -> ECS / Splunk TA fields
│       ├── fake.hql         # class windows -> fake databases
│       ├── live.hql         # class windows -> elastic / splunk
│       └── sources.hql      # picks fake or live
├── data/
│   ├── windows-process.ndjson   # ECS process events (Elastic stand-in)
│   └── windows-security.ndjson  # 4769 events (Splunk stand-in)
├── rules/                   # unmodified SigmaHQ rules
└── hac/
    ├── kerberoasting.hql               # straight Sigma conversion
    ├── kerberoasting_threshold.hql     # adds the threshold the Sigma rule asks for
    └── powershell_then_kerberoast.hql  # Elastic + Splunk join on client IP
```

## Running

Notebook:

```bash
uv sync --group notebooks
uv run marimo edit examples/deathcon-26/deathcon.py
```

CLI, from the repo root (`local-base` in `config/fake.yml` is relative to the CWD):

```bash
uv run python -m Hql -c examples/deathcon-26/config -f examples/deathcon-26/hac/kerberoasting_threshold.hql
uv run python -m Hql -c examples/deathcon-26/config -f examples/deathcon-26/rules/win_security_kerberoasting_activity.yml
```

Add `-nx` to compile only, or `-dpar` to print the deparsed Hql.

## Going live

- Fill in `config/splunk.yml` (and `config/elastic.yml` if you have one). Config doesn't read env vars, so don't commit secrets; `git update-index --skip-worktree <file>` keeps local edits out of git.
- Change `config/maps/sources.hql` to `import maps.live;`. To go live with only Splunk, change just the `security` line in `config/maps/fake.hql`.
- Caveats:
  - In live mode the HaC time bound only applies to the first source compiled (bug workspace-vuc).
  - Elastic `host.ip` is an array and Splunk `Client_Address` may be `::ffff:`-prefixed, so the join in `powershell_then_kerberoast.hql` may need normalising.

## Attribution

The files in `rules/` are unmodified SigmaHQ rules under the [Detection Rule License 1.1](https://github.com/SigmaHQ/Detection-Rule-License); authors are credited in each rule. The HaC files are derived works and keep the original authors, links and license.
