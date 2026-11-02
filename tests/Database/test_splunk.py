from Hql.Compiler import HqlCompiler
from Hql.Config import Config
from Hql.Parser.Sigma import SigmaParser


RULE = r'''
title: Not filter
status: test
description: Selection with a filter excluded
logsource:
    category: process_creation
    product: windows
detection:
    selection:
        Image|endswith: '\cmd.exe'
    filter:
        User: SYSTEM
    condition: selection and not filter
'''


def test_sigma_class_simple_compile():
    conf = Config()
    conf.add_database('test', {'name': 'splunk', 'type': 'Splunk', 'conf': {'host': 'localhost'}})
    conf.load_sigma('test', {'header': "class windows = { let process_creation = database('splunk').index('main') }"})

    parser = SigmaParser(RULE, conf)
    parser.assemble()
    root = HqlCompiler(conf, query=parser.assembly, hac=parser.gen_hac(), time=False).root

    out = root.upstream[0].simple_compile()

    assert out['index'] == 'main'
    assert out['query'].startswith('search ')
    # SPL may render the filter as `search User="SYSTEM"` or `where User == "SYSTEM"`
    assert 'NOT (User' in out['query'] and '"SYSTEM")' in out['query']
    assert 'index="main"' in out['query']
