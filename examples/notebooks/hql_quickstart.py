import marimo

__generated_with = "0.23.13"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    from pathlib import Path
    from importlib import reload
    import json

    import Hql

    import logging
    logging.getLogger().setLevel(logging.DEBUG)
    return Hql, Path, json, mo


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    # Hql quickstart

    This notebook runs an [Hql](https://github.com/Hashfastr/Hql) query from
    Python and shows the result as a table. It uses the repo's local `json`
    example database (`local-data/tf11-so-network.json`), so it works fully
    offline — no Elasticsearch/Splunk/etc. required.

    Edit the query below and the results further down will re-run automatically.
    See `examples/notebooks/README.md` for setup instructions.
    """)
    return


@app.cell(hide_code=True)
def _(Path, mo):
    # conf/ lives at the repo root; this notebook lives two levels below it
    # (examples/notebooks/), so resolve it relative to this file rather than cwd.
    conf_dir = Path(__file__).resolve().parents[2] / "conf"

    mo.stop(
        not conf_dir.is_dir(),
        mo.md(
            f"""
            **No config found at `{conf_dir}`.**

            Set one up first, from the repo root:

            ```
            cp -r conf.example conf
            ```

            Then re-run this notebook.
            """
        ).callout(kind="danger"),
    )
    return (conf_dir,)


@app.cell
def _():
    sigma = r'''
    title: Kalambur Backdoor Curl TOR SOCKS Proxy Execution
    id: e99375eb-3ee0-407a-9f90-79569cc6a01c
    status: experimental
    description: Detects the execution of the "curl.exe" command, referencing "SOCKS" and ".onion" domains, which could be indicative of Kalambur backdoor activity.
    references:
        - https://blog.eclecticiq.com/sandworm-apt-targets-ukrainian-users-with-trojanized-microsoft-kms-activation-tools-in-cyber-espionage-campaigns
    author: Arda Buyukkaya (EclecticIQ)
    date: 2025-02-11
    tags:
        - attack.command-and-control
        - attack.t1090
        - attack.t1573
        - attack.t1071.001
        - attack.t1059.001
        - attack.s0183
        - detection.emerging-threats
    logsource:
        category: process_creation
        product: windows
    detection:
        selection_img:
            Image|endswith: '\curl.exe'
        selection_socks:
            CommandLine|contains:
                - 'socks5h://'
                - 'socks5://'
                - 'socks4a://'
        selection_onion:
            CommandLine|contains: '.onion'
        condition: all of selection_*
    falsepositives:
        - Unlikely
    level: high
    '''
    return (sigma,)


@app.cell
def _(Hql, conf_dir, sigma):
    from Hql.Parser.Sigma import SigmaParser

    # sets the target in the config for a given database then compiles it with that target
    def compile_with_target(target:str) -> dict:
        from Hql.Compiler.Hql import HqlCompiler

        conf = Hql.Config.Config(conf_dir)

        # conf defined above in a collapsed cell
        parser = SigmaParser(sigma, conf)
        parser.assemble()
        if parser.assembly:
            print('Valid sigma parsed!')
        else:
            return {'index': '', 'query': ''}
        #print(json.dumps(parser.assembly.to_dict(), indent=2))

        elastic_conf = conf.get_database('tf11-elastic')
        elastic_conf['conf']['compiler'] = target
        conf.set_database('tf11-elastic', elastic_conf)

        # precompilation
        compiler = HqlCompiler(conf, query=parser.assembly, hac=parser.gen_hac())

        # compilation
        return compiler.root.upstream[0].simple_compile()

    return (compile_with_target,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Precompilation
    The HqlCompiler precompiles the target.
    This handles mapping by filtering operators through project and extend operators.
    Depending on your database, or how you wish to compile, the filtering project and extend operators will not be shown in the final database query.
    Should your database not handle such operators, elastic cough, then operators will run post query using the database results.

    Taken from the above function:
    ```python
    compiler = HqlCompiler(conf, query=parser.assembly, hac=parser.gen_hac())
    ```
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Simple compilation
    This allows one to just get the compilation for a database without running the engine.
    If the backend supports multiple language targets then the configured target is used.

    Below is using QueryDSL, the default configured in this case.
    Note that the fields defined in the above sigma are now replaced by their mapped fields.
    """)
    return


@app.cell
def _(compile_with_target, json):
    dsl_compiled = compile_with_target('dsl')
    print('index: ' + dsl_compiled['index'])
    print('query: ' + json.dumps(dsl_compiled['query'], indent=2))
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Below is using Lucene, to allow for this we will override DSL in the config to Lucene.
    Since we are swapping languages we will need to re-preprocess although Lucene is not much different than DSL in feature set.
    Once of these you will see is that case sensitive compare in lucene is dubious to my understanding, so a warning will flair.

    Compilation is now as simple as DSL.
    It may be easier to see here but time bounding is automatic in perspective of the HaC definition.
    Sigma inherits a 1hr time window for a query, and can be changed.
    """)
    return


@app.cell
def _(compile_with_target):
    lucene_compiled = compile_with_target('lucene')
    print('index: ' + lucene_compiled['index'])
    print('query: ' + lucene_compiled['query'])
    return


if __name__ == "__main__":
    app.run()
