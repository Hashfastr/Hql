from Hql.Compiler.Compiler import Compiler
from Hql.Expressions.Literals import Integer
from Hql.Operators.Count import Count
from Hql.Operators.Take import Take
from Hql.Operators.Where import Where
from Hql.Expressions.Logic import Equality
from Hql.Expressions.References import NamedReference


class TestLuceneCompiler:
    def test_type_matches_class_name(self):
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
        


        assert Compiler().type == "Compiler"
        


NOT_RULE = r'''
title: Not filter
status: test
description: Selection with filters excluded
logsource:
    category: process_creation
    product: windows
detection:
    selection:
        Image|endswith: '\cmd.exe'
    filter_system:
        User: SYSTEM
    filter_service:
        User: LOCAL SERVICE
    condition: {condition}
'''


def compile_sigma(condition, compiler):
    from Hql.Compiler import HqlCompiler
    from Hql.Config import Config
    from Hql.Parser.Sigma import SigmaParser

    parser = SigmaParser(NOT_RULE.format(condition=condition), Config())
    parser.assemble()
    where = parser.assembly.statements[-1].root.pipes[0]
    desc, _ = HqlCompiler(Config()).compile(where)
    compiler.add_op(desc)
    query, _ = compiler.compile(None, prep=False)
    return query


class TestNot:
    def test_lucene_not(self):
        from Hql.Compiler import LuceneCompiler

        query = compile_sigma('selection and not filter_system', LuceneCompiler())
        assert isinstance(query, str)
        # BinaryLogic doesn't preserve order
        assert sorted(query.split(' AND ')) == ['(NOT User:"SYSTEM")', 'Image:/.*\\\\cmd\\.exe/']

    def test_lucene_not_binary_logic_is_parenthesized(self):
        from Hql.Compiler import LuceneCompiler

        query = compile_sigma('selection and not 1 of filter_*', LuceneCompiler())
        assert isinstance(query, str)
        assert ' AND ' in query
        negated = [x for x in query.split(' AND ') if x.startswith('(NOT')][0]
        assert negated in (
            '(NOT (User:"SYSTEM" OR User:"LOCAL SERVICE"))',
            '(NOT (User:"LOCAL SERVICE" OR User:"SYSTEM"))',
        )

    def test_dsl_not(self):
        from Hql.Compiler import QueryDSLCompiler

        query = compile_sigma('selection and not filter_system', QueryDSLCompiler())
        assert isinstance(query, dict)
        must = query['bool']['must']
        assert {'bool': {'must_not': {'term': {'User': 'SYSTEM'}}}} in must


class TestEmptyRoot:
    def test_lucene_compile_without_root_returns_pair(self):
        from Hql.Compiler import LuceneCompiler

        acc, rej = LuceneCompiler().compile(None, prep=False)
        assert not isinstance(acc, tuple)
        assert rej is None

    def test_dsl_function_compile_returns_pair(self):
        from Hql.Compiler import QueryDSLCompiler
        from Hql.Functions.null import isnull

        acc, rej = QueryDSLCompiler().compile(isnull([NamedReference('f')]))
        assert not isinstance(acc, tuple)
        assert rej is None
