import marimo

__generated_with = "0.25.2"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import json
    import logging
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
        mo,
        run_query,
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

    Everything runs offline against small fake databases in `data/`.
    Put your real Splunk/Elastic in `config/splunk.yml` / `config/elastic.yml` (see `README.md`).
    """)
    return


@app.cell(hide_code=True)
def _(Path, mo):
    HERE = Path(__file__).resolve().parent
    CONFIG = HERE / "config"
    RULES = HERE / "rules"
    DATA = HERE / "data"
    HAC = HERE / "hac"

    CURL_UPLOAD = "proc_creation_lnx_susp_curl_fileupload.yml"
    ENCODED_PS = "proc_creation_win_powershell_base64_encoded_cmd.yml"
    KERBEROAST = "win_security_kerberoasting_activity.yml"

    mo.stop(
        not CONFIG.is_dir(),
        mo.md(f"**No config found at `{CONFIG}`.**").callout(kind="danger"),
    )
    return CONFIG, CURL_UPLOAD, DATA, ENCODED_PS, HAC, KERBEROAST, RULES


@app.cell
def _(CONFIG, Config, DATA, HqlCompiler, RULES, SigmaParser, mo):
    def rule(name):
        return (RULES / name).read_text()

    # read-only editor shows text as-is; mo.md re-renders fenced blocks with extra newlines.
    # sql is the closest highlighter to Hql/SPL.
    def code(text, lang="sql"):
        return mo.ui.code_editor(value=text.strip(), language=lang, disabled=True)

    def load_config(header=None):
        conf = Config(CONFIG)
        # local-base is relative to the working directory, pin it to this folder
        for _name in ("fake-elastic", "fake-splunk"):
            conf.get_database(_name)["conf"]["local-base"] = str(DATA)
        # config/sigma.yml points raw Sigma at TF11, this notebook stays offline
        conf.conf["sigma"]["header"] = header or "import maps.sources"
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
def _(CONFIG, code, mo):
    mo.ui.tabs({
        _f: code((CONFIG / _f).read_text(), "yaml" if _f.endswith(".yml") else "sql")
        for _f in ("sigma.yml", "maps/fields.hql", "maps/live.hql", "elastic.yml", "splunk.yml")
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
def _(CONFIG, DATA, code, mo):
    mo.ui.tabs({
        "maps/sources.hql": code((CONFIG / "maps/sources.hql").read_text()),
        "maps/fake.hql": code((CONFIG / "maps/fake.hql").read_text()),
        "windows-process.ndjson": code((DATA / "windows-process.ndjson").read_text(), "json"),
        "windows-security.ndjson": code((DATA / "windows-security.ndjson").read_text(), "json"),
    })
    return


@app.cell
def _(ENCODED_PS, KERBEROAST, load_config, mo, rule, run_query, show):
    conf = load_config()
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


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### The HaC engine

    The engine loads every detection in `hac/`, fires each on its `@schedule`,
    and serves a web UI for managing, running and viewing them.
    Each detection runs once on start so the UI has results right away.

    The web UI needs free-threaded Python (`3.14t`) and a built `Hql-Interface/dist`.
    """)
    return


@app.cell
def _(mo):
    start_engine = mo.ui.run_button(label="Start the HaC engine")
    start_engine
    return (start_engine,)


@app.cell
def _(
    CONFIG,
    HAC,
    HacEngine,
    load_config,
    mo,
    socket,
    start_engine,
    sys,
    threading,
    time,
    uvicorn,
    webbrowser,
):
    mo.stop(not start_engine.value)

    class DemoEngine(HacEngine):
        def load_conf(self):
            return load_config()  # fake databases pinned to data/

    engine = DemoEngine(HAC, True, CONFIG)
    mo.stop(
        engine.apiserver is None,
        mo.md("The web UI needs free-threaded Python (`3.14t`).").callout(kind="warn"),
    )

    # the web server logs from its own thread, which marimo can't capture: send it to the terminal
    for _handler in uvicorn.config.LOGGING_CONFIG["handlers"].values():
        _handler["stream"] = sys.__stderr__

    for _detection in engine.detections.values():
        engine.run_detection(_detection)
    threading.Thread(target=engine.run, daemon=True).start()

    # wait up to 5s for the server to accept connections, then open the UI in a new tab
    _url = f"http://localhost:{engine.apiserver.port}"
    for _ in range(50):
        try:
            socket.create_connection(("localhost", engine.apiserver.port), timeout=0.1).close()
            break
        except OSError:
            time.sleep(0.1)
    webbrowser.open_new_tab(_url)

    mo.md(f"HaC engine running {len(engine.detections)} detections from `hac/`: [{_url}]({_url})")
    return


if __name__ == "__main__":
    app.run()
