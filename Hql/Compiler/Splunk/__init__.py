from __future__ import annotations
from typing import Optional, Union, TYPE_CHECKING, Callable

from Hql.Exceptions import HqlExceptions as hqle
from Hql.Context import Context
import logging
import io

from ..Compiler import Compiler

if TYPE_CHECKING:
    from Hql.Compiler import BranchDescriptor, InstructionSet
    from Hql.Operators.Operator import Operator
    from Hql.Expressions import Expression
    from Hql.Expressions.Logic import Logic
    from Hql.Expressions.Logic import Equality
    from Hql.Query import Statement
    import Hql

class SPLCompiler(Compiler):
    """Compile supported HQL pipelines into Splunk Processing Language."""

    def __init__(self, time_format:str="%Y-%m-%dT%H:%M:%S.%f%z"):
        from Hql.Data import Data
        from Hql.Compiler import HqlCompiler
        from Hql.Config import Config
        self.type = self.__class__.__name__
        self.ctx = Context(Data())
        self.ops:list[Operator] = []
        self.symbols = dict()
        self.post_ops:list[Operator] = []
        self.vestigial_compiler = HqlCompiler(Config())
        self.top_level_expr:Optional[Logic] = None
        self.time_format = time_format

        # self.reserved_names = {
        #     'index': 
        # }

        self.supported_functions = {
            'count': 'count',
            'tolower': 'lower'
        }

    def from_name(self, name:str) -> Callable:
        if hasattr(self, name):
            return getattr(self, name)
        raise hqle.CompilerException(f'Attempting to get non-existant compiler function for {name}')

    def run(self, ctx:Union[Context, None]=None) -> Context:
        ctx = ctx if ctx else self.ctx
        return self.ctx

    def add_op(self, op:Union[Operator, BranchDescriptor]) -> tuple[Optional[Operator], Optional[Operator]]:
        from Hql.Compiler import BranchDescriptor
        from Hql.Operators.Operator import Operator
        if isinstance(op, BranchDescriptor):
            op = op.get_op()
        acc, rej = self.compile(op)

        if isinstance(acc, list):
            self.ops += acc
        elif acc:
            assert isinstance(acc, Operator)
            self.ops.append(acc)

        assert isinstance(rej, (Operator, type(None)))
        return None, rej

    def optimize(self, ops: list[BranchDescriptor]) -> list[BranchDescriptor]:
        return ops

    def add_top_level(self, op:Hql.Operators.Where) -> Optional[Hql.Operators.Where]:
        from Hql.Expressions.Logic import BinaryLogic
        acc, _ = self.vestigial_compiler.compile(op)
        where = acc.get_attr('functions') or acc.get_attr('regex_matching') or acc.get_attr('case_sensitive_compare')

        if where:
            return op

        if not self.top_level_expr:
            self.top_level_expr = op.expr
        elif isinstance(self.top_level_expr, BinaryLogic) and self.top_level_expr.logic_and:
            self.top_level_expr.exprs.append(op.expr)
        else:
            self.top_level_expr = BinaryLogic([self.top_level_expr, op.expr])
        
        return None

    '''
    You'll want to replace this with something like a string that you'll query your database with.
    Default returns optimized operators for running in Hql-land
    '''
    def compile(self, src:Union[Expression, Operator, Statement, None], prep:bool=True, where:bool=False) -> tuple[Optional[object], Optional[object]]:
        from Hql.Operators import ProjectAway
        from Hql.Expressions.References import Wildcard, NamedReference
        from Hql.Expressions.Logic import Equality, Logic
        from Hql.Expressions.Literals import StringLiteral

        if src == None:
            ops:list[str] = []
            for i in self.ops:
                acc, rej = self.compile(i, prep=False)
                if rej:
                    logging.warning(f'Non-preprocess op {i} returned non-None rejection {rej}')
                assert isinstance(acc, str)
                ops.append(acc)

            junk = ProjectAway([NamedReference('_raw'), Wildcard('_*')])
            acc, _ = self.compile(junk, prep=False)
            assert isinstance(acc, str)
            ops.append(acc)

            if not self.top_level_expr:
                self.top_level_expr = Equality(NamedReference('index'), [StringLiteral('*', verbatim=True)])
            acc, _ = self.compile(self.top_level_expr, prep=False)
            ops = [f'search {acc}'] + ops

            # ops.append('| extract')

            return '\n'.join(ops), None

        # Only predicates care whether they're rendered for search or where
        if isinstance(src, Logic):
            return self.from_name(src.type)(src, prep=prep, where=where)
        return self.from_name(src.type)(src, prep=prep)

    '''
    By default, all of these return themselves as they are being
    'rejected' back to the compiler
    '''

    '''
    Splunk ops
    '''

    # def Spath(self, op:Spath, prep:bool=True) -> tuple[object, None]:
    #     if prep:
    #         return op, None
    #
    #     return 

    '''
    Operators
    '''

    def Where(self, op:Hql.Operators.Where, prep:bool=True) -> tuple[object, object]:
        from Hql.Operators.Where import Where
        from Hql.Types.Hql import HqlTypes as hqlt
        from Hql.Expressions.Logic import Logic

        acc, _ = self.vestigial_compiler.compile(op.expr)
        where = acc.get_attr('functions') or acc.get_attr('regex_matching') or acc.get_attr('case_sensitive_compare')

        types = acc.get_attr('types')
        if isinstance(types, list) and hqlt.datetime in [type(x) for x in types]:
            where = True

        if prep:
            acc, rej = self.compile(op.expr)
            assert isinstance(acc, (Logic, type(None)))
            assert isinstance(rej, (Logic, type(None)))
            ret_acc = Where(acc) if acc else None
            ret_rej = Where(rej) if rej else None
        
            if ret_acc and not self.ops and not where:
                ret_acc = self.add_top_level(ret_acc)

            return ret_acc, ret_rej

        acc, _ = self.compile(op.expr, prep=False, where=where)
        assert isinstance(acc, str)
        pred = acc

        if where:
            spl_op = 'where'
        else:
            spl_op = 'search'

        acc = f'| {spl_op} ' + pred
        return acc, None

    def Project(self, op:Hql.Operators.Project, prep:bool=True) -> tuple[object, object]:
        from Hql.Expressions.References import NamedExpression, NamedReference
        from Hql.Operators.Extend import Extend
        from Hql.Operators.Project import Project

        if prep:
            extend = []
            project = []
            for i in op.exprs:
                acc, rej = self.vestigial_compiler.compile(i)
                
                if acc.get_attr('functions'):
                    if isinstance(i, NamedExpression):
                        extend.append(i)
                        for j in i.paths:
                            project.append(j)
                    else:
                        return None, op
                elif isinstance(i, NamedExpression):
                    extend.append(i)
                    for j in i.paths:
                        project.append(j)
                else:
                    assert isinstance(i, NamedReference)
                    project.append(i)

            if extend:
                extend = Extend(extend)
                acc, rej = self.compile(extend)
                if rej:
                    return None, op
                extend = acc

            project = Project(project)

            if extend:
                return [extend, project], None
            else:
                return project, None

        exprs = []
        for i in op.exprs:
            acc, _ = self.compile(i, prep=False)
            exprs.append(acc)
        
        acc = f'| fields ' + ', '.join(exprs)
        return acc, None

    def ProjectAway(self, op:Hql.Operators.ProjectAway, prep:bool=True) -> tuple[object, object]:
        if prep:
            return op, None

        exprs = []
        for i in op.exprs:
            acc, _ = self.compile(i, prep=False)
            exprs.append(acc)
        
        acc = f'| fields - ' + ', '.join(exprs)
        return acc, None

    def ProjectKeep(self, op:Hql.Operators.ProjectKeep, prep:bool=True) -> tuple[object, object]:
        if prep:
            return op, None

        exprs = []
        for i in op.exprs:
            acc, _ = self.compile(i, prep=False)
            exprs.append(acc)
        
        acc = f'| fields ' + ', '.join(exprs)
        return acc, None

    def ProjectReorder(self, op:Hql.Operators.ProjectReorder, prep:bool=True) -> tuple[object, object]:
        if prep:
            return op, None

        exprs = []
        for i in op.exprs:
            acc, _ = self.compile(i, prep=False)
            exprs.append(acc)
        exprs.append('*')
        
        acc = f'| fields ' + ', '.join(exprs)
        return acc, None

    def ProjectRename(self, op:Hql.Operators.ProjectRename, prep:bool=True) -> tuple[object, object]:
        from Hql.Expressions.References import NamedExpression
        from Hql.Expressions.References import Reference
        if prep:
            for i in op.exprs:
                if not isinstance(i, NamedExpression):
                    return None, op
                if len(i.paths) > 1:
                    return None, op
            return op, None

        exprs = []
        for i in op.exprs:
            assert isinstance(i, NamedExpression)
            assert isinstance(i.value, Reference)
            path, _ = self.compile(i.paths[0], prep=False)
            value, _ = self.compile(i.value, prep=False)
            assert isinstance(path, str)
            assert isinstance(value, str)
            exprs.append(value + ' AS ' + path)

        acc = f'| rename ' + ', '.join(exprs)
        return acc, None

    def Take(self, op:Hql.Operators.Take, prep:bool=True) -> tuple[object, object]:
        if prep:
            if op.tables:
                return None, op
            return op, None

        acc, _ = self.compile(op.expr, prep=False)
        assert isinstance(acc, int)
        acc = f'| head {acc}'

        return acc, None

    def Count(self, op:Hql.Operators.Count, prep:bool=True) -> tuple[object, object]:
        if prep:
            if op.name:
                return None, op
            return op, None

        ret = '| stats count by index'
        return ret, None

    def Extend(self, op:Hql.Operators.Extend, prep:bool=True) -> tuple[object, object]:
        from Hql.Operators.Extend import Extend
        if prep:
            exprs = []
            rejexprs = []
            for i in op.exprs:
                acc, rej = self.compile(i)
                if rej:
                    rejexprs.append(i)
                else:
                    exprs.append(acc)

            acc = Extend(exprs) if exprs else None
            rej = Extend(rejexprs) if rejexprs else None
            return acc, rej

        parts = []
        for i in op.exprs:
            acc, rej = self.compile(i, prep=False)
            assert isinstance(acc, str)
            parts.append(acc)
        exprs = ', '.join(parts)

        out = '| eval ' + exprs
        return out, None

    def Range(self, op:Hql.Operators.Range, prep:bool=True) -> tuple[object, object]:
        from Hql.Expressions.Literals import Integer, Float, Datetime
        if prep:
            return op, None

        out = ''

        acc, _ = self.compile(op.name, prep=False)
        assert isinstance(acc, str)
        name = acc

        if isinstance(op.start, (Integer, Float)):
            acc, _ = self.compile(op.start, prep=False)
            assert isinstance(acc, int)
            start = acc

            acc, _ = self.compile(op.end, prep=False)
            assert isinstance(acc, int)
            end = acc

            acc, _ = self.compile(op.step, prep=False)
            assert isinstance(acc, int)
            step = acc

            out = f'''
            | makeresults
            | eval {name} = mvrange({start}, {end}, {step})
            | mvexpand {name}
            | table {name}
            '''
        
        elif isinstance(op.start, Datetime):
            acc, _ = self.compile(op.start, prep=False)
            assert isinstance(acc, str)
            start = acc

            acc, _ = self.compile(op.end, prep=False)
            assert isinstance(acc, str)
            end = acc

            acc, _ = self.compile(op.start, prep=False)
            assert isinstance(acc, str)
            step = acc

            out = f'''
            | makeresults
            | eval start_time = {start}
            | eval end_time = {end}
            | eval step_seconds = {step}
            | eval {name} = mvrange(start_time, end_time, step_seconds)
            | mvexpand {name}
            | table {name}
            '''

        else:
            raise hqle.CompilerException(f'Invalid range type {type(op.start)}')
        
        return out, op

    def Top(self, op:Hql.Operators.Top, prep:bool=True) -> tuple[object, object]:
        return None, op

    def Unnest(self, op:Hql.Operators.Unnest, prep:bool=True) -> tuple[object, object]:
        return None, op

    def Union(self, op:Hql.Operators.Union, prep:bool=True) -> tuple[object, object]:
        return None, op

    def Summarize(self, op:Hql.Operators.Summarize, prep:bool=True) -> tuple[object, object]:
        return None, op

    def Datatable(self, op:Hql.Operators.Datatable, prep:bool=True) -> tuple[object, object]:
        from Hql.Expressions.References import NamedReference
        from Hql.Expressions.Literals import Literal
        import csv

        if prep:
            return op, None

        keys:list[str] = []
        for i in op.schema:
            assert isinstance(i[0], NamedReference)
            keys.append(i[0].name)

        data = []
        row = dict()
        for i in range(0, len(op.values), len(keys)):
            for idx, j in enumerate(op.values[i:i+len(keys)]):
                assert isinstance(j, Literal)
                row[keys[idx]] = j.value
            data.append(row)
            row = dict()

        out = io.StringIO()
        writer = csv.DictWriter(out, fieldnames=keys)
        writer.writeheader()
        writer.writerows(data)
        csvout = out.getvalue()

        new = '| makeresults format=csv data='
        new += '"""\n'
        new += csvout
        new += '\n"""'

        return new, op

    def Join(self, op:Hql.Operators.Join, prep:bool=True) -> tuple[object, object]:
        return None, op

    def MvExpand(self, op:Hql.Operators.MvExpand, prep:bool=True) -> tuple[object, object]:
        from Hql.Operators.MvExpand import MvExpand
        if prep:
            supported = []
            failed = []
            for i in op.exprs:
                if i.to:
                    failed.append(i)
                else:
                    supported.append(i)
            acc = MvExpand(supported)
            rej = MvExpand(failed)
            return acc, rej

        exprs = []
        for i in op.exprs:
            acc, rej = self.compile(i.expr, prep=False)
            assert isinstance(acc, str)
            exprs.append(acc)

        if op.limit:
            acc, rej = self.compile(op.limit, prep=False)
            assert isinstance(acc, int)
            limit = acc
        else:
            limit = None

        out = ''
        for i in exprs:
            out += '| mvexpand ' + i
            if limit != None:
                out += f' limit={limit}'
            out += '\n'
        
        return out, None

    def Sort(self, op:Hql.Operators.Sort, prep:bool=True) -> tuple[object, object]:
        if prep:
            for i in op.exprs:
                if i.nulls != 'last':
                    return None, op
            return op, None

        exprs = []
        for i in op.exprs:
            field, _ = self.compile(i.expr, prep=False)
            assert isinstance(field, str)
            order = '-' if i.order == 'desc' else '+'
            exprs.append(order + field)
        exprs = ', '.join(exprs)

        out = '| sort ' + exprs
        return out, None

    def Rename(self, op:Hql.Operators.Rename, prep:bool=True) -> tuple[object, object]:
        return None, op

    '''
    Expressions
    '''

    def Tabular(self, expr:Hql.Expressions.Expression) -> tuple[Optional[InstructionSet], Optional[Hql.Expressions.Expression]]:
        return None, expr

    def PipeExpression(self, expr:Hql.Expressions.PipeExpression, prep:bool=True) -> tuple[object, object]:
        return None, expr

    def OpParameter(self, expr:Hql.Expressions.OpParameter, prep:bool=True) -> tuple[object, object]:
        return None, expr

    def ToClause(self, expr:Hql.Expressions.ToClause, prep:bool=True) -> tuple[object, object]:
        return None, expr

    def OrderedExpression(self, expr:Hql.Expressions.OrderedExpression, prep:bool=True) -> tuple[object, object]:
        return expr, None

    def ByExpression(self, expr:Hql.Expressions.ByExpression, prep:bool=True) -> tuple[object, object]:
        return expr, None


    def Function(self, expr:Hql.Functions.Function, prep:bool=True) -> tuple[object, object]:
        if prep:
            if expr.name not in self.supported_functions:
                return None, expr

            for i in expr.args:
                _, rej = self.compile(i)
                if rej:
                    return None, expr

            return expr, None

        args = []
        for i in expr.args:
            acc, _ = self.compile(i, prep=False)
            args.append(str(acc))
        args = ', '.join(args)
        name = self.supported_functions[expr.name]

        return f'{name}({args})', None

    def LogicFunction(self, expr:Hql.Functions.Logic.LogicFunction, prep:bool=True, where:bool=False) -> tuple[object, object]:
        return None, expr

    def DotCompositeFunction(self, expr:Hql.Functions.DotCompositeFunction, prep:bool=True) -> tuple[object, object]:
        return None, expr

    def Equality(self, expr:Equality, prep:bool=True, where:bool=False) -> tuple[object, object]:
        from Hql.Expressions.Logic import Equality, BasicRange, BetweenEquality, BinaryLogic
        from Hql.Expressions.References import Reference
        from Hql.Expressions import Expression

        if prep:
            # Break out BasicRange right hands into BetweenEqualities
            ranges = [x for x in expr.rh if isinstance(x, BasicRange)]
            if ranges:
                exprs = [BetweenEquality(expr.lh, x.start, x.end, neq=expr.neq) for x in ranges]
                rest = [x for x in expr.rh if not isinstance(x, BasicRange)]
                if rest:
                    exprs.append(Equality(expr.lh, rest, cs=expr.cs, neq=expr.neq))
                # x !in (a, b) == x != a and x != b
                return self.compile(BinaryLogic(exprs, logic_and=expr.neq))

            lh, rej = self.compile(expr.lh)
            if rej:
                return None, expr
            assert isinstance(lh, Reference)

            rh = []
            for i in expr.rh:
                acc, rej = self.compile(i)
                if rej:
                    return None, expr
                assert isinstance(acc, Expression)
                rh.append(acc)

            return Equality(lh, rh, neq=expr.neq, cs=expr.cs), None

        lh, _ = self.compile(expr.lh, prep=False)

        rh = []
        for i in expr.rh:
            acc, _ = self.compile(i, prep=False)
            rh.append(str(acc))

        if where:
            if expr.cs:
                if len(rh) > 1:
                    out = f'in({lh}, ' + ', '.join(rh) + ')'
                else:
                    out = f'{lh} == {rh[0]}'
            else:
                pairs = []
                for i in rh:
                    pairs.append(f'lower({lh}) == lower({i})')
                out = ' OR '.join(pairs)
                if len(pairs) > 1:
                    out = f'({out})'

        else:
            pairs = []
            for i in rh:
                pairs.append(f'{lh}={i}')
            out = ' OR '.join(pairs)
            if len(pairs) > 1:
                out = f'({out})'

        if expr.neq:
            out = f'NOT ({out})'

        return out, None

    def Substring(self, expr:Hql.Expressions.Logic.Substring, prep:bool=True, where:bool=False) -> tuple[object, object]:
        from Hql.Expressions.Logic import Substring
        from Hql.Expressions.References import Reference
        from Hql.Expressions.Literals import StringLiteral
        import re

        if prep:
            lh, rej = self.compile(expr.lh)
            if rej:
                return None, expr
            assert isinstance(lh, Reference)

            rh = []
            for i in expr.rh:
                acc, rej = self.compile(i)
                if rej:
                    return None, expr
                assert isinstance(acc, StringLiteral)
                rh.append(acc)

            new = Substring(
                lh,
                rh,
                term=expr.term,
                logic_and=expr.logic_and,
                neq=expr.neq,
                cs=expr.cs,
                startswith=expr.startswith,
                endswith=expr.endswith
            )
            return new, None

        lh, _ = self.compile(expr.lh, prep=False)
        assert isinstance(lh, str)

        pairs = []
        for i in expr.rh:
            if where:
                value = re.escape(i.str())
                if expr.startswith:
                    value = '^' + value
                elif expr.endswith:
                    value = value + '$'
                if not expr.cs:
                    value = '(?i)' + value
            else:
                if expr.startswith:
                    value = i.str() + '*'
                elif expr.endswith:
                    value = '*' + i.str()
                else:
                    value = '*' + i.str() + '*'

            new = StringLiteral(value, verbatim=True)
            acc, _ = self.compile(new, prep=False)
            assert isinstance(acc, str)

            if where:
                pairs.append(f'match({lh}, {acc})')
            else:
                pairs.append(f'{lh}={acc}')

        out = (' AND ' if expr.logic_and else ' OR ').join(pairs)
        if len(pairs) > 1:
            out = f'({out})'

        if expr.neq:
            out = f'NOT ({out})'

        return out, None

    def Relational(self, expr:Hql.Expressions.Logic.Relational, prep:bool=True, where:bool=False) -> tuple[object, object]:
        from Hql.Expressions.Logic import Relational
        from Hql.Expressions.References import Reference
        from Hql.Expressions import Expression

        if prep:
            lh, rej = self.compile(expr.lh)
            if rej:
                return None, expr
            assert isinstance(lh, Reference)

            rh, rej = self.compile(expr.rh[0])
            if rej:
                return None, expr
            assert isinstance(rh, Expression)

            return Relational(lh, rh, expr.gt, expr.eq), None

        lh, _ = self.compile(expr.lh, prep=False)
        assert isinstance(lh, str)

        rh, _ = self.compile(expr.rh[0], prep=False)

        return f'{lh} {expr.build_op()} {rh}', None

    def BetweenEquality(self, expr:Hql.Expressions.Logic.BetweenEquality, prep:bool=True, where:bool=False) -> tuple[object, object]:
        from Hql.Expressions.Logic import BetweenEquality
        from Hql.Expressions.References import Reference
        from Hql.Expressions.Literals import Literal

        if prep:
            lh, rej = self.compile(expr.lh)
            if rej:
                return None, expr
            assert isinstance(lh, Reference)

            start, rej = self.compile(expr.start)
            if rej:
                return None, expr
            assert isinstance(start, Literal)

            end, rej = self.compile(expr.end)
            if rej:
                return None, expr
            assert isinstance(end, Literal)

            return BetweenEquality(lh, start, end, neq=expr.neq), None

        lh, _ = self.compile(expr.lh, prep=False)
        start, _ = self.compile(expr.start, prep=False)
        end, _ = self.compile(expr.end, prep=False)

        out = f'({lh} >= {start} AND {lh} <= {end})'
        if expr.neq:
            out = f'NOT {out}'

        return out, None

    def BinaryLogic(self, expr:Hql.Expressions.Logic.BinaryLogic, prep:bool=True, where:bool=False) -> tuple[object, object]:
        from Hql.Expressions.Logic import BinaryLogic

        if prep:
            accs = []
            rejs = []
            for i in expr:
                acc, rej = self.compile(i)

                # Partially accepted nested logic can't be split safely
                if isinstance(i, BinaryLogic) and rej:
                    rejs.append(i)
                    continue

                if acc:
                    accs.append(acc)
                if rej:
                    rejs.append(rej)

            # Cannot salvage an or with any rejected branch
            if rejs and not expr.logic_and:
                return None, expr

            acc = BinaryLogic(accs, logic_and=expr.logic_and) if accs else None
            rej = BinaryLogic(rejs, logic_and=expr.logic_and) if rejs else None
            return acc, rej

        exprs = []
        for i in expr:
            acc, _ = self.compile(i, prep=False, where=where)
            assert isinstance(acc, str)
            if isinstance(i, BinaryLogic):
                acc = f'({acc})'
            exprs.append(acc)

        out = (' AND ' if expr.logic_and else ' OR ').join(exprs)
        return out, None

    def Not(self, expr:Hql.Expressions.Logic.Not, prep:bool=True, where:bool=False) -> tuple[object, object]:
        from Hql.Expressions.Logic import Not, Logic

        if prep:
            if not isinstance(expr.expr, Logic):
                return None, expr

            acc, rej = self.compile(expr.expr)
            if rej:
                return None, expr
            assert isinstance(acc, Logic)
            return Not(acc), None

        inner, _ = self.compile(expr.expr, prep=False, where=where)
        return f'NOT ({inner})', None

    def BasicRange(self, expr:Hql.Expressions.Logic.BasicRange, prep:bool=True, where:bool=False) -> tuple[object, object]:
        return None, expr

    def Regex(self, expr:Hql.Expressions.Logic.Regex, prep:bool=True, where:bool=False) -> tuple[object, object]:
        from Hql.Expressions.References import Reference
        from Hql.Expressions.Literals import StringLiteral

        if prep:
            if expr.g:
                return None, expr

            lh, rej = self.compile(expr.lh)
            if rej:
                return None, expr
            assert isinstance(lh, Reference)

            rh, rej = self.compile(expr.rh)
            if rej:
                return None, expr
            assert isinstance(rh, StringLiteral)

            expr.lh = lh
            expr.rh = rh

            return expr, None

        # | where match(dest_mac, "(?sim)00:50:56:ef:8C:19")
        lh, _ = self.compile(expr.lh, prep=False)

        flags = '(?'
        if expr.i:
            flags += 'i'
        if expr.s:
            flags += 's'
        if expr.m:
            flags += 'm'
        flags += ')'
        if flags == '(?)':
            flags = ''

        rh = StringLiteral(flags + expr.rh.str(), verbatim=True)
        rh, _ = self.compile(rh, prep=False)

        out = f'match({lh}, {rh})'
        return out, None

    def TypeExpression(self, expr:Hql.Expressions.Literals.TypeExpression, prep:bool=True) -> tuple[object, object]:
        return None, expr

    def StringLiteral(self, expr:Hql.Expressions.Literals.StringLiteral, prep:bool=True) -> tuple[object, object]:
        if prep:
            return expr, None
        return expr.quote('"'), None

    def MultiString(self, expr:Hql.Expressions.Literals.MultiString, prep:bool=True) -> tuple[object, object]:
        from Hql.Expressions.Literals import StringLiteral

        # Component strings are already escaped, don't escape again
        return self.StringLiteral(StringLiteral(expr.str(), verbatim=True), prep=prep)

    def Integer(self, expr:Hql.Expressions.Literals.Integer, prep:bool=True) -> tuple[object, object]:
        if prep:
            return expr, None
        return expr.value, None

    def IP4(self, expr:Hql.Expressions.Literals.IP4, prep:bool=True) -> tuple[object, object]:
        return None, expr

    def Float(self, expr:Hql.Expressions.Literals.Float, prep:bool=True) -> tuple[object, object]:
        if prep:
            return expr, None
        return str(expr.value), None

    def Bool(self, expr:Hql.Expressions.Literals.Bool, prep:bool=True, where:bool=False) -> tuple[object, object]:
        if prep:
            return expr, None
        ret = 'true' if expr.value else 'false'
        return ret, None

    def Multivalue(self, expr:Hql.Expressions.Literals.Multivalue, prep:bool=True) -> tuple[object, object]:
        return None, expr

    def Datetime(self, expr:Hql.Expressions.Literals.Datetime, prep:bool=True) -> tuple[object, object]:
        from Hql.Expressions.Literals import StringLiteral
        if prep:
            return expr, None

        acc = StringLiteral(expr.render(self.time_format), verbatim=True)
        datelit, _ = self.compile(acc, prep=False)
        acc = StringLiteral(self.time_format, verbatim=True)
        time_format, _ = self.compile(acc, prep=False)

        func = f'strptime({datelit}, {time_format})'
        return func, None

    def NamedReference(self, expr:Hql.Expressions.References.NamedReference, prep:bool=True) -> tuple[object, object]:
        if prep:
            return expr, None
        return expr.name, None

    def EscapedNamedReference(self, expr:Hql.Expressions.References.EscapedNamedReference, prep:bool=True) -> tuple[object, object]:
        if prep:
            return expr, None
        return f'{repr(expr.name)}', None

    def Wildcard(self, expr:Hql.Expressions.References.Wildcard, prep:bool=True) -> tuple[object, object]:
        return self.NamedReference(expr, prep=prep)

    def Path(self, expr:Hql.Expressions.References.Path, prep:bool=True) -> tuple[object, object]:
        if prep:

            '''
            spath = False
            for i in expr.path:
                if isinstance(i, EscapedNamedReference):
                    spath = True

            # Create a compiler workaround
            if spath:
                parts = []
                for i in expr.path:
                    if isinstance(i, EscapedNamedReference):
                        parts.append(f"'{i.name}'")
                    else:
                        parts.append(i.name)
                rh = StringLiteral('.'.join(parts), lquote='@"', rquote='"')

                lh = NamedReference('%16x' % random.getrandbits(64))
                self.symbols[expr] = lh

                reassign = ProjectRename('project-rename', [NamedExpression([expr], lh)])
                self.post_ops.append(reassign)

                self.ops.append(Spath(lh, rh))
                return lh, None
            '''

            return expr, None

        parts = []
        for i in expr.path:
            parts.append(i.name)
        out = repr('.'.join(parts))
        return out, None

    def NamedExpression(self, expr:Hql.Expressions.References.NamedExpression, prep:bool=True) -> tuple[object, object]:
        from Hql.Expressions.References import NamedExpression

        if prep:
            good_paths = []
            bad_paths = []
            for i in expr.paths:
                acc, rej = self.compile(i)
                if rej:
                    bad_paths.append(rej)
                else:
                    good_paths.append(acc)

            # Function handles its own support checks
            value, rej = self.compile(expr.value)
            if rej or not good_paths:
                return None, expr

            good = NamedExpression(good_paths, value)
            bad = None
            if bad_paths:
                bad = NamedExpression(bad_paths, value)

            return good, bad

        paths = []
        for i in expr.paths:
            acc, _ = self.compile(i, prep=False)
            assert isinstance(acc, str)
            paths.append(acc)

        # eval context, so any logic needs where syntax
        value, _ = self.compile(expr.value, prep=False, where=True)
        value = str(value)

        exprs = []
        for i in paths:
            exprs.append(f'{i}={value}')

        return ', '.join(exprs), None
