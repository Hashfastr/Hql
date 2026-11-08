import marimo

__generated_with = "0.25.2"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import json
    import logging
    import shutil
    import socket
    import sys
    import threading
    import time
    import uvicorn
    import webbrowser
    from pathlib import Path

    from Hql.Config import Config
    from Hql.Compiler import HqlCompiler, LuceneCompiler, QueryDSLCompiler, KQLCompiler, SPLCompiler
    from Hql.Parser.Sigma import SigmaParser
    from Hql.Helpers import run_query
    from Hql.Hac.Engine import Detection, HacEngine

    logging.getLogger().setLevel(logging.WARNING)
    return (
        Config,
        Detection,
        HacEngine,
        HqlCompiler,
        KQLCompiler,
        LuceneCompiler,
        Path,
        QueryDSLCompiler,
        SPLCompiler,
        SigmaParser,
        json,
        logging,
        mo,
        run_query,
        shutil,
        socket,
        sys,
        threading,
        time,
        uvicorn,
        webbrowser,
    )


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Hql @ DEATHCon 2026

    One query language from Sigma rule to results:

    1. **Sigma in, four languages out**: compile Sigma to Lucene, Elastic DSL, KQL and SPL with no database at all.
    2. **One config, two backends**: route one Sigma rule to Elastic and another to Splunk, mapping fields on the way.
    3. **Run Sigma against the databases**: same rules, actual results.
    4. **Hql as Code (HaC)**: Hql's Sigma alternative. Convert rules, then do what Sigma can't.
    5. **The HaC engine on the static dataset**: schedule the detections and manage them in a web UI.
    6. **The HaC engine on a Log Analytics workspace**: the same engine against your own Sentinel data.

    There are two configs:

    - `config/static/`: sections 1 to 5. They run offline against small fake databases in `data/`.
      Put your real Splunk/Elastic in `config/static/splunk.yml` / `elastic.yml` (see `README.md`).
    - `config/azure/`: section 6. It needs a workspace in `config/azure/loganalytics.yml` and an `az login`.
    """)
    return


@app.cell(hide_code=True)
def _(Path, mo):
    HERE = Path(__file__).resolve().parent
    STATIC_CONFIG = HERE / "config" / "static"
    AZURE_CONFIG = HERE / "config" / "azure"
    RULES = HERE / "rules"
    DATA = HERE / "data"
    HAC = HERE / "hac"
    HAC_LA = HERE / "hac-loganalytics"

    CURL_UPLOAD = "proc_creation_lnx_susp_curl_fileupload.yml"
    ENCODED_PS = "proc_creation_win_powershell_base64_encoded_cmd.yml"
    KERBEROAST = "win_security_kerberoasting_activity.yml"

    _missing = [_c for _c in (STATIC_CONFIG, AZURE_CONFIG) if not _c.is_dir()]
    mo.stop(
        bool(_missing),
        mo.md(f"**No config found at `{_missing[0] if _missing else ''}`.**").callout(kind="danger"),
    )
    return (
        AZURE_CONFIG,
        CURL_UPLOAD,
        DATA,
        ENCODED_PS,
        HAC,
        HAC_LA,
        KERBEROAST,
        RULES,
        STATIC_CONFIG,
    )


@app.cell
def _(Config, DATA, HqlCompiler, RULES, STATIC_CONFIG, SigmaParser, mo):
    def rule(name):
        return (RULES / name).read_text()

    # read-only editor shows text as-is; mo.md re-renders fenced blocks with extra newlines.
    # sql is the closest highlighter to Hql/SPL.
    def code(text, lang="sql"):
        return mo.ui.code_editor(value=text.strip(), language=lang, disabled=True)

    # config/static, with the header in its sigma.yml (TF11) unless one is given
    def load_config(header=None):
        conf = Config(STATIC_CONFIG)
        # local-base is relative to the working directory, pin it to this folder
        for _name in ("fake-elastic", "fake-splunk"):
            conf.get_database(_name)["conf"]["local-base"] = str(DATA)
        if header:
            conf.conf["sigma"]["header"] = header
        return conf

    # Sigma -> one backend language. No config, no database, no field mapping.
    def raw_compile(sigma, compiler):
        parser = SigmaParser(sigma, Config())
        parser.assemble()
        where = parser.assembly.statements[-1].root.pipes[0]
        desc, _ = HqlCompiler(Config()).compile(where)  # preprocess, e.g. not() -> Not
        _, rejected = compiler.add_op(desc)
        query, _ = compiler.compile(None, prep=False)
        return query, rejected

    # Sigma -> the database its logsource routes to, plus what Hql runs after it
    def precompile(sigma, conf):
        parser = SigmaParser(sigma, conf)
        parser.assemble()
        root = HqlCompiler(conf, query=parser.assembly, time=False).root
        return root.upstream[0], [op.deparse() for op in root.ops]

    def show(data):
        return mo.vstack([mo.vstack([mo.md(f"**{t.name}**: {len(t.df)} rows"), t.df]) for t in data])

    return code, load_config, precompile, raw_compile, rule, show


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 1. Sigma in, four languages out

    A SigmaHQ rule, compiled straight to each backend's language.
    There's no config and no database here, so field names stay as Nextron wrote them.

    Anything a language can't express is *left for Hql*: it runs on the results instead.
    KQL has no regex, for example, so the `|re` part of this rule stays in Hql.
    """)
    return


@app.cell
def _(CURL_UPLOAD, code, rule):
    code(rule(CURL_UPLOAD), "yaml")
    return


@app.cell
def _(
    CURL_UPLOAD,
    KQLCompiler,
    LuceneCompiler,
    QueryDSLCompiler,
    SPLCompiler,
    code,
    json,
    mo,
    raw_compile,
    rule,
):
    _compilers = {
        "Lucene": LuceneCompiler(),
        "Elastic DSL": QueryDSLCompiler(),
        "KQL (Kibana)": KQLCompiler(),
        "SPL (Splunk)": SPLCompiler(),
    }

    _tabs = {}
    for _name, _compiler in _compilers.items():
        _query, _rejected = raw_compile(rule(CURL_UPLOAD), _compiler)
        _out = [code(json.dumps(_query, indent=2), "json") if isinstance(_query, dict) else code(_query)]
        if _rejected:
            _out.append(mo.md(f"Left for Hql: `{_rejected.deparse()}`"))
        _tabs[_name] = mo.vstack(_out)
    mo.ui.tabs(_tabs)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 2. One config, two backends

    A Sigma `logsource` becomes `product('windows').category('process_creation')` (or `.service('security')`).
    Those resolve against the classes in the config's sigma header:

    - `windows.process_creation` → **Elastic**, ECS fields
    - `windows.security` → **Splunk**, Splunk Add-on for Windows fields

    A `map` renames Sigma's field names to the backend's, so the rules themselves never change.
    """)
    return


@app.cell
def _(STATIC_CONFIG, code, mo):
    mo.ui.tabs({
        _f: code((STATIC_CONFIG / _f).read_text(), "yaml" if _f.endswith(".yml") else "sql")
        for _f in ("maps/fields.hql", "maps/live.hql", "elastic.yml", "splunk.yml")
    })
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Compiling the two rules against the real backends. Nothing connects, so placeholder configs are fine.

    Elastic gets its query in ECS names, then Hql renames the results back.
    Splunk does the renaming itself in SPL.
    """)
    return


@app.cell
def _(ENCODED_PS, KERBEROAST, code, json, load_config, mo, precompile, rule):
    _live = load_config("import maps.live")

    _tabs = {}
    for _name in (ENCODED_PS, KERBEROAST):
        _db, _after = precompile(rule(_name), _live)
        _compiled = _db.simple_compile()
        _query = _compiled["query"]
        _tabs[_name] = mo.vstack([
            mo.md(f"**{_db.type}** `{_db.name}`, index `{_compiled['index']}`"),
            code(_query) if isinstance(_query, str) else code(json.dumps(_query, indent=2), "json"),
            mo.md("Hql runs after: " + (", ".join(f"`{_op}`" for _op in _after) or "nothing")),
        ])
    mo.ui.tabs(_tabs)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 3. Run Sigma against the databases

    Same rules, same maps, but `maps/sources.hql` points the classes at fake databases:
    two JSON files shaped like Elastic and Splunk data.
    To go live, change `sources.hql` to `import maps.live;`.
    """)
    return


@app.cell
def _(DATA, STATIC_CONFIG, code, mo):
    mo.ui.tabs({
        "maps/sources.hql": code((STATIC_CONFIG / "maps/sources.hql").read_text()),
        "maps/fake.hql": code((STATIC_CONFIG / "maps/fake.hql").read_text()),
        "windows-process.ndjson": code((DATA / "windows-process.ndjson").read_text(), "json"),
        "windows-security.ndjson": code((DATA / "windows-security.ndjson").read_text(), "json"),
    })
    return


@app.cell
def _(ENCODED_PS, KERBEROAST, load_config, mo, rule, run_query, show):
    conf = load_config("import maps.sources")
    mo.ui.tabs({_name: show(run_query(rule(_name), conf)) for _name in (ENCODED_PS, KERBEROAST)})
    return (conf,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 4. Hql as Code

    HaC is a Hql query with a doc comment on top: the metadata lives with the query,
    and `@schedule` drives the engine and the query's time window.

    First, Sigma converts directly:
    """)
    return


@app.cell
def _(Config, Detection, KERBEROAST, code, rule):
    code(Detection(rule(KERBEROAST), KERBEROAST, Config()).deparse())
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Then it can do what Sigma can't:

    - `kerberoasting.hql`: the straight conversion.
    - `kerberoasting_threshold.hql`: adds the threshold the Sigma rule's own description asks for, using `summarize`.
    - `powershell_then_kerberoast.hql`: joins Elastic process events with Splunk Kerberos events from the same host.
    """)
    return


@app.cell
def _(Detection, HAC, code, conf, mo, show):
    _tabs = {}
    for _path in sorted(HAC.glob("*.hql")):
        _text = _path.read_text()
        _detection = Detection(_text, str(_path), conf)
        _tabs[_path.name] = mo.vstack([
            mo.md(_detection.hac.render("md")),
            code(_text.split("*/", 1)[1].strip()),
            show(_detection.run().data),
        ])
    mo.ui.tabs(_tabs)
    return


@app.cell
def _(
    HacEngine,
    logging,
    mo,
    socket,
    sys,
    threading,
    time,
    uvicorn,
    webbrowser,
):
    # Logging goes to marimo's stderr, which only takes writes from the thread running a cell.
    # Detections run in engine threads, send their records to the terminal instead.
    # Compared as Thread objects: an ident is reused once its thread exits, and an engine
    # thread given the cell's old ident would write to marimo outside of any cell.
    class EngineLogs(logging.StreamHandler):
        def __init__(self, cell_thread):
            super().__init__()
            self.cell_thread = cell_thread

        def emit(self, record):
            in_cell = threading.current_thread() is self.cell_thread
            self.setStream(sys.stderr if in_cell else sys.__stderr__)
            super().emit(record)

    # Starts an engine over every detection in directory, with configs from make_conf
    def launch_engine(directory, config_dir, make_conf, port):
        # Re-running this cell redefines EngineLogs, so match the old handler by name
        _root = logging.getLogger()
        for _h in [x for x in _root.handlers if type(x).__name__ == 'EngineLogs']:
            _root.removeHandler(_h)
        _root.addHandler(EngineLogs(threading.current_thread()))

        class DemoEngine(HacEngine):
            def load_conf(self):
                return make_conf()

        engine = DemoEngine(directory, True, config_dir)
        if engine.apiserver is None:
            return mo.md("The web UI needs free-threaded Python (`3.14t`).").callout(kind="warn")
        # one port per engine, so both can run at once
        engine.apiserver.port = port

        # the web server logs from its own thread, which marimo can't capture: send it to the terminal
        for _handler in uvicorn.config.LOGGING_CONFIG["handlers"].values():
            _handler["stream"] = sys.__stderr__

        for _detection in engine.detections.values():
            engine.run_detection(_detection)
        threading.Thread(target=engine.run, daemon=True).start()

        # wait up to 5s for the server to accept connections, then open the UI in a new tab
        _url = f"http://localhost:{port}"
        for _ in range(50):
            try:
                socket.create_connection(("localhost", port), timeout=0.1).close()
                break
            except OSError:
                time.sleep(0.1)
        webbrowser.open_new_tab(_url)

        return mo.md(
            f"HaC engine running {len(engine.detections)} detections from `{directory.name}/`: [{_url}]({_url})"
        )

    return (launch_engine,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 5. The HaC engine on the static dataset

    The engine loads every detection in `hac/`, fires each on its `@schedule`,
    and serves a web UI for managing, running and viewing them.
    Each detection runs once on start so the UI has results right away.

    This engine uses `config/static/`. Its `sigma.yml` points raw Sigma rules at the TF11
    mappings (`maps/tf11.hql`), so a SigmaHQ rule dropped into `hac/` hunts the TF11 datasets.
    The HaC files in `hac/` import `maps.sources` themselves, so they keep running on the fake
    Elastic and Splunk databases in `data/`.

    The web UI needs free-threaded Python (`3.14t`) and a built `Hql-Interface/dist`.
    """)
    return


@app.cell
def _(mo):
    start_static_engine = mo.ui.run_button(label="Start the HaC engine on the static dataset")
    start_static_engine
    return (start_static_engine,)


@app.cell
def _(HAC, STATIC_CONFIG, launch_engine, load_config, mo, start_static_engine):
    mo.stop(not start_static_engine.value)

    # fake databases pinned to data/, raw Sigma on TF11
    launch_engine(HAC, STATIC_CONFIG, load_config, 8080)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 6. The HaC engine on a Log Analytics workspace

    The same engine, pointed at a Log Analytics workspace (Microsoft Sentinel's tables live here)
    with `config/azure/`. Its `sigma.yml` points raw Sigma rules at the Azure mappings (`maps/azure.hql`):
    Sigma logsources over the Azure Monitor tables, with Sigma field names.
    It loads the detections in `hac-loganalytics/`, which import `maps.azure` too.

    - `azurehound_signin.hql`: sign-ins with AzureHound's user agent, from `SigninLogs`.
    - `password_spray.hql`: many failed sign-ins from one IP address, a threshold Sigma can't express.

    The where clauses run in the workspace as KQL, and each run's time window is sent as the query timespan.

    To set it up:

    1. Put the Workspace ID from the workspace's Overview blade in `config/azure/loganalytics.yml`.
    2. Run `az login` as someone with Log Analytics Reader on the workspace. Hql uses that session, no secret needed.

    This engine's web UI is on port 8081, so it can run next to the static one.
    """)
    return


@app.cell
def _(AZURE_CONFIG, HAC_LA, code, mo):
    mo.ui.tabs({
        "loganalytics.yml": code((AZURE_CONFIG / "loganalytics.yml").read_text(), "yaml"),
        "sigma.yml": code((AZURE_CONFIG / "sigma.yml").read_text(), "yaml"),
        **{_path.name: code(_path.read_text()) for _path in sorted(HAC_LA.glob("*.hql"))},
    })
    return


@app.cell
def _(mo):
    start_la_engine = mo.ui.run_button(label="Start the HaC engine on Log Analytics")
    start_la_engine
    return (start_la_engine,)


@app.cell
def _(AZURE_CONFIG, Config, HAC_LA, launch_engine, mo, shutil, start_la_engine):
    mo.stop(not start_la_engine.value)

    def la_config():
        return Config(AZURE_CONFIG)

    _workspace = la_config().get_database("loganalytics")["conf"].get("workspace_id", "")
    mo.stop(
        not _workspace or _workspace.startswith("<"),
        mo.md("Put your Workspace ID in `config/azure/loganalytics.yml` first.").callout(kind="warn"),
    )
    mo.stop(
        shutil.which("az") is None,
        mo.md("The Azure CLI (`az`) isn't on `PATH`. Install it and run `az login`.").callout(kind="warn"),
    )

    launch_engine(HAC_LA, AZURE_CONFIG, la_config, 8081)
    return


if __name__ == "__main__":
    app.run()
