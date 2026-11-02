from copy import deepcopy

import pytest

from Hql.Compiler import HqlCompiler
from Hql.Config import Config
from Hql.Database import Elasticsearch
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


def elastic_config(compiler='lucene'):
    return {
        'name': 'elastic',
        'type': 'Elasticsearch',
        'conf': {'hosts': ['https://localhost:9200'], 'compiler': compiler},
    }


def test_elasticsearch_copy_shares_client():
    # Client construction does not connect
    db = Elasticsearch(elastic_config())
    db.add_index('logs-*')

    copied = deepcopy(db)

    assert copied is not db
    assert copied.client is db.client
    assert copied.compiler is not db.compiler
    assert copied.pattern == 'logs-*'


@pytest.mark.parametrize('compiler', ['lucene', 'dsl'])
def test_sigma_class_simple_compile(compiler):
    conf = Config()
    conf.add_database('test', elastic_config(compiler))
    conf.load_sigma('test', {'header': "class windows = { let process_creation = database('elastic').index('logs-*') }"})

    parser = SigmaParser(RULE, conf)
    parser.assemble()
    root = HqlCompiler(conf, query=parser.assembly, hac=parser.gen_hac(), time=False).root

    out = root.upstream[0].simple_compile()

    assert out['index'] == 'logs-*'
    if compiler == 'lucene':
        assert '(NOT User:"SYSTEM")' in out['query']
    else:
        assert {'bool': {'must_not': {'term': {'User': 'SYSTEM'}}}} in out['query']['bool']['must']
