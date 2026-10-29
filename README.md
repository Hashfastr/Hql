# Hash Query Language (Hql)
<p align="center">
  <img src="https://hql.dev/hql-dark-no-text.png" width="300" />
  <h3>Current Phase: Cambrian - Ultra Alpha</h3>
  <s>Current Phase: Primordial Ooze</s>
</p>



Hash Query Language (Hql) is a query language designed to implement a consistent feature set across all database backends.
Is this accomplished by using a modified grammar of [Kusto Query Language](https://github.com/microsoft/Kusto-Query-Language) (KQL), a query language by Microsoft made for Azure Data Explorer, the basis for Log Analytics Workspace.
This enables the use of alternative database backends such as Elasticsearch or SQLite without compromising on capabilities.

The inspiration of Hql comes from the frustration of using Graylog with my personal homelab after setting it up at [DEATHCON](https://deathcon.io) 2024, see [the original rant idea here](docs/MANIFESTO.md).
The implementation differs from Kusto in that it supports and embraces nosql datasets, instead of a proprietary backend structured SQL-like database.
There are also many other feature changes, **it is a completely different language**, but aims to replicate Kusto's capabilities/feature set, and is largely compatible with Kusto.

Hql provides some features not supported by Kusto, such as joining between disparate databases and datasets:

```
let ElasticZeek = database("tf11-elastic").index("so-network-2022.10")
| where event.module == "zeek"
| extend IPAddress = source.ip;
database("sentinel").SigninLogs
| where Username == "iamcompromised"
| project IPAddress
| join type=inner ElasticZeek on IPAddress
| summarize count() by destination.ip, destination.port, source.ip, source.port
```

In the above we found an attacker IOC in Azure, aka o365, and were able to instantly pivot to the zeek logs we have in Elasticsearch.
Replace Elastic with Splunk and you get a great usecase, joining cloud to on-prem.

Where a given backend does not support a given feature, such as analytic functions and Lucene, it gets implemented by Hql.
Below, lines 1-3 are able to be collapsed into a single query to elastic.
The results are returned and ingested into a [polars](https://docs.pola.rs/) DataFrame, which then the follow operations are done:

1. extend
    - A new column Hostname in the DataFrame is created with the contents of winlog.computer_name
    - Column event.code is cast to INT64 and assigned to column EventID.
2. project
    - The column EventID is fed into series_stats generating a dict with keys for each stat value.
    - Since this function is provided as the single expression, with no assigned name, it gets expanded as the new output DataFrame.

```
1 database("tf11-elastic").index("so-beats-2022.10.*")
2 | where ['@timestamp'] between ("2022-10-21T15:45:00.000Z" .. "2022-10-21T15:55:00.000Z")
3 | where winlog.computer_name == "asarea.vxnwua.net"
4 | extend Hostname = winlog.computer_name, EventID = toint(event.code)
5 | project series_stats(EventID)
```

Resulting in:

```
[{"series_stats_EventID_min": 1, "series_stats_EventID_min_idx": 105, "series_stats_EventID_max": 16394, "series_stats_EventID_max_idx": 225, "series_stats_EventID_avg": 1709.3838936669272, "series_stats_EventID_stdev": 2257.263833183075, "series_stats_EventID_variance": 5095240.012596348}]
```

The use of Polars as the backend compute engine allows for super fast processing.
The three main limiters of performance right now across the board are:

1. IO wait on databases, scrolling, etc
2. Parsing since it's still done in python.
3. Launching the program

## Detection as Code
Hql is detection as code native.
It accepts Sigma queries directly and can instantly query then against your environment.
Generic source definitions and field mappings are part of the compiler, allowing for definitions to be effortless.
Sigma is also expanded to include two new fields defining a cron schedule and post-sigma instructions, such as pushing to a soar.

```
title: Headless Process Launched Via Conhost.EXE
id: 00ca75ab-d5ce-43be-b86c-55ff39c6abfc
related:
    - id: 056c7317-9a09-4bd4-9067-d051312752ea
      type: derived
schedule: '* * * * *'
status: test
description: |
    Detects the launch of a child process via "conhost.exe" with the "--headless" flag.
    The "--headless" flag hides the windows from the user upon execution.
references:
    - https://www.huntress.com/blog/fake-browser-updates-lead-to-boinc-volunteer-computing-software
author: Nasreddine Bencherchali (Nextron Systems)
date: 2024-07-23
tags:
    - attack.defense-evasion
    - attack.t1059.001
    - attack.t1059.003
    - detection.threat-hunting
logsource:
    category: process_creation
    product: windows
detection:
    selection:
        ParentImage|endswith: '\conhost.exe'
        ParentCommandLine|contains: '--headless'
    condition: selection
    posthql: scot4
falsepositives:
    - Unknown
level: medium
```

Hql also carries documentation with the code, so it never leaves the detection, enabling true detection as code.
Defined as a Deoxygen style comment, the Hql as Code (HaC) metadata is carried with the query, allowing it to be used within the language.

```
/**
 * @title Set Files as System Files Using Attrib.EXE
 * @id bb19e94c-59ae-4c15-8c12-c563d23fe52b
 * @status test
 * @schedule 0 * * * *
 * 
 * @description
 * Detects the execution of "attrib" with the "+s" flag to mark files as system files
 * 
 * @author frack113
 * @related
 * - {'id': 'efec536f-72e8-4656-8960-5e85d091345b', 'type': 'similar'}
 * 
 * @references
 * - https://github.com/redcanaryco/atomic-red-team/blob/f339e7da7d05f6057fdfcdd3742bfcf365fee2a9/atomics/T1564.001/T1564.001.md#atomic-test-3---create-windows-system-file-with-attrib
 * - https://docs.microsoft.com/en-us/windows-server/administration/windows-commands/attrib
 * - https://unit42.paloaltonetworks.com/unit42-sure-ill-take-new-combojack-malware-alters-clipboards-steal-cryptocurrency/
 * 
 * @date 2022-02-04
 * @modified 2023-03-14
 * @tags
 * - attack.defense-evasion
 * - attack.t1564.001
 * - detection.threat-hunting
 * 
 * @falsepositives
 * - Unknown
 * 
 * @level low
 */
product('windows').category('process_creation')
| where Image endswith '\\attrib.exe' or OriginalFileName in ('ATTRIB.EXE')
| where CommandLine contains_any (' +s ')
```

Sigma queries can also be instantly converted to this HaC format with the use of a flag.
The above is a direct conversion, and allows for immediate improvements over Sigma's feature set.

```
python3 -m Hql -dpar -v -f ./proc_creation_win_attrib_system.yml > proc_creation_win_attrib_system.hql
```

HaC can also be initialized on a query as such, auto generating a guid and date:

```
python3 -m Hql --init-hac -v -f ./new-detection.hql
```

## HaC Engine
To complete the system, HaC queries can be run within a multi-threaded engine, decoupling detections from their limited platforms.
For example, Sentinel does not allow you to delete detections, and redeploying detections changes the firing times, generating duplicates.
This runs on a laptop, enabling quick set up for whatever environment you must hunt on.
Auto schedules detections and ensures they run on a timely manner.

There is also a **vibe coded** interface at http://localhost:8081 which allows you to interact with it.
Manage detections, run, and view.
The API also exists on this port.

See [docs/HaC/ENGINE.md](docs/HaC/ENGINE.md) for the engine's execution chain and threading design.

## Implemented features **out of date**
See the implemented features [here](docs/features/README.md).
I'll put these into issues at some point.

Might be better to look at closed issues until I get to documentation.

## Running
The repo is pinned to Python 3.14t (free-threaded) via `.python-version` for multi-threading and HaC engine support.
If you use Python 3.14t, prepare to build polars, requiring a good toolchain.
There's also a container for convienence.

[uv](https://docs.astral.sh/uv/) handles the interpreter and the venv:

```
# copy and configure Hql
cp -r conf.example conf

# uv reads .python-version and creates .venv automatically
uv sync

## OR pypi

uv pip install pyhql

## OR container (replaced podman with docker as needed)

podman pull hashfastr/hql:latest
# add z as needed
# use as a replacement for python3 -m Hql
podman run -v .:/data:z -it hashfastr/hql:latest --help

# make your first query
uv run python -m Hql -v -f ./examples/databases/json/json.hql

# run sigma, requires Sigma source definitions
uv run python -m Hql -v -f ./examples/sigma/rules-threat-hunting/windows/process_creation/proc_creation_win_attrib_system.yml

# convert sigma
git submodule init
uv run python -m Hql -v -dpar -f ./examples/sigma/rules-threat-hunting/windows/process_creation/proc_creation_win_attrib_system.yml

# Start HaC engine
uv run python -m Hql -v -eng -d ./examples/interface
```
