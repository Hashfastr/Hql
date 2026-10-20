from __future__ import annotations
from typing import Optional, Sequence, Union, TYPE_CHECKING, Callable

from Hql.Exceptions import HqlExceptions as hqle
from Hql.Context import Context
import logging
import csv, json
import io

from ..Compiler import Compiler

if TYPE_CHECKING:
    from Hql.Compiler import BranchDescriptor, InstructionSet
    from Hql.Operators.Operator import Operator
    from Hql.Expressions import Expression
    from Hql.Expressions.Logic import Logic
    from Hql.Query import Statement
    from Hql.Config import Config
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
    def compile(self, src:Union[Expression, Operator, Statement, None], prep:bool=True, **kwargs) -> tuple[Optional[object], Optional[object]]:
        # from Hql.Expressions.Logic import Equality, NamedReference, Wildcard, StringLiteral
        # from Hql.Operators.ProjectAway import ProjectAway
        from Hql.Operators import ProjectAway
        from Hql.Expressions.References import Wildcard, NamedReference
        from Hql.Expressions.Logic import Equality
        from Hql.Expressions.Literals import StringLiteral

        if src == None:
            ops:list[str] = []
            for i in self.ops:
                acc, rej = self.compile(i, preprocess=False)
                if rej:
                    logging.warning(f'Non-preprocess op {i} returned non-None rejection {rej}')
                assert isinstance(acc, str)
                ops.append(acc)

            junk = ProjectAway([NamedReference('_raw'), Wildcard('_*')])
            acc, _ = self.compile(junk, preprocess=False)
            assert isinstance(acc, str)
            ops.append(acc)

            if not self.top_level_expr:
                self.top_level_expr = Equality(NamedReference('index'), [StringLiteral('*', verbatim=True)])
            acc, _ = self.compile(self.top_level_expr, preprocess=False)
            ops = [f'search {acc}'] + ops

            # ops.append('| extract')

            return '\n'.join(ops), None

        return self.from_name(src.type)(src, prep=prep, where=kwargs.get('where', False))

    '''
    By default, all of these return themselves as they are being
    'rejected' back to the compiler
    '''

    '''
    Splunk ops
    '''

    # def Spath(self, op:Spath, prep:bool=True, **kwargs) -> tuple[object, None]:
    #     if prep:
    #         return op, None
    #
    #     return 

    '''
    Operators
    '''

    def Where(self, op:Hql.Operators.Where, prep:bool=True) -> tuple[object, object]:
        from Hql.Operators.Where import Where
        from Hql.Expressions import Expression
        from Hql.Types.Hql import HqlTypes as hqlt

        acc, _ = self.vestigial_compiler.compile(op.expr)
        where = acc.get_attr('functions') or acc.get_attr('regex_matching') or acc.get_attr('case_sensitive_compare')

        types = acc.get_attr('types')
        if isinstance(types, list) and hqlt.datetime in [type(x) for x in types]:
            where = True

        if prep:
            acc, rej = self.compile(op.expr)
            assert isinstance(acc, (Expression, type(None)))
            assert isinstance(rej, (Expression, type(None)))
            ret_acc = Where(acc) if acc else None
            ret_rej = Where(rej) if rej else None
        
            if ret_acc and not self.ops and not where:
                ret_acc = self.add_top_level(ret_acc)

            return ret_acc, ret_rej

        acc, _ = self.compile(op.expr, preprocess=False, where=where)
        assert isinstance(acc, str)
        pred = acc

        if where:
            spl_op = 'where'
        else:
            spl_op = 'search'

        acc = f'| {spl_op} ' + pred
        return acc, None

    def Project(self, op:Hql.Operators.Project, prep:bool=True, **kwargs) -> tuple[object, object]:
        from Hql.Expressions.References import NamedExpression, NamedReference
        from Hql.Operators.Extend import Extend, Project
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

            project = Project('project', project)

            if extend:
                return [extend, project], None
            else:
                return project, None

        exprs = []
        for i in op.exprs:
            acc, _ = self.compile(i, preprocess=False)
            exprs.append(acc)
        
        acc = f'| fields ' + ', '.join(exprs)
        return acc, None

    def ProjectAway(self, op:Hql.Operators.ProjectAway, prep:bool=True, **kwargs) -> tuple[object, object]:
        if prep:
            return op, None

        exprs = []
        for i in op.exprs:
            acc, _ = self.compile(i, preprocess=False)
            exprs.append(acc)
        
        acc = f'| fields - ' + ', '.join(exprs)
        return acc, None

    def ProjectKeep(self, op:Hql.Operators.ProjectKeep, prep:bool=True, **kwargs) -> tuple[object, object]:
        if prep:
            return op, None

        exprs = []
        for i in op.exprs:
            acc, _ = self.compile(i, preprocess=False)
            exprs.append(acc)
        
        acc = f'| fields ' + ', '.join(exprs)
        return acc, None

    def ProjectReorder(self, op:Hql.Operators.ProjectReorder, prep:bool=True, **kwargs) -> tuple[object, object]:
        if prep:
            return op, None

        exprs = []
        for i in op.exprs:
            acc, _ = self.compile(i, preprocess=False)
            exprs.append(acc)
        exprs.append('*')
        
        acc = f'| fields ' + ', '.join(exprs)
        return acc, None

    def ProjectRename(self, op:Hql.Operators.ProjectRename, prep:bool=True, **kwargs) -> tuple[object, object]:
        from Hql.Expressions.References import NamedExpression
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
            path, _ = self.compile(i.paths[0], preprocess=False)
            value, _ = self.compile(i.value, preprocess=False)
            assert isinstance(path, str)
            assert isinstance(value, str)
            exprs.append(value + ' AS ' + path)

        acc = f'| rename ' + ', '.join(exprs)
        return acc, None

    def Take(self, op:Hql.Operators.Take, prep:bool=True, **kwargs) -> tuple[object, object]:
        if prep:
            if op.tables:
                return None, op
            return op, None

        acc, _ = self.compile(op.expr, preprocess=False)
        assert isinstance(acc, int)
        acc = f'| head {acc}'

        return acc, None

    def Count(self, op:Hql.Operators.Count, prep:bool=True, **kwargs) -> tuple[object, object]:
        if prep:
            if op.name:
                return None, op
            return op, None

        ret = '| stats count by index'
        return ret, None

    def Extend(self, op:Hql.Operators.Extend, prep:bool=True, **kwargs) -> tuple[object, object]:
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
            acc, rej = self.compile(i, preprocess=False)
            assert isinstance(acc, str)
            parts.append(acc)
        exprs = ', '.join(parts)

        out = '| eval ' + exprs
        return out, None

    def Range(self, op:Hql.Operators.Range, prep:bool=True, **kwargs) -> tuple[object, object]:
        from Hql.Expressions.Literals import Integer, Float, Datetime
        if prep:
            return op, None

        acc, rej = self.compile(op.name, preprocess=False)
        assert isinstance(acc, str)
        name = acc

        if isinstance(op.start, (Integer, Float)):
            acc, rej = self.compile(op.start, preprocess=False)
            assert isinstance(acc, int)
            start = acc

            acc, rej = self.compile(op.end, preprocess=False)
            assert isinstance(acc, int)
            end = acc

            acc, rej = self.compile(op.step, preprocess=False)
            assert isinstance(acc, int)
            step = acc

            out = f'''
            | makeresults
            | eval {name} = mvrange({start}, {end}, {step})
            | mvexpand {name}
            | table {name}
            '''
        
        elif isinstance(op.start, Datetime):
            acc, rej = self.compile(op.start, preprocess=False)
            assert isinstance(acc, str)
            start = acc

            acc, rej = self.compile(op.end, preprocess=False)
            assert isinstance(acc, str)
            end = acc

            acc, rej = self.compile(op.start, preprocess=False)
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

    def Top(self, op:Hql.Operators.Top, prep:bool=True, **kwargs) -> tuple[object, object]:
        return None, op

    def Unnest(self, op:Hql.Operators.Unnest, prep:bool=True, **kwargs) -> tuple[object, object]:
        return None, op

    def Union(self, op:Hql.Operators.Union, prep:bool=True, **kwargs) -> tuple[object, object]:
        return None, op

    def Summarize(self, op:Hql.Operators.Summarize, prep:bool=True, **kwargs) -> tuple[object, object]:
        return None, op

    def Datatable(self, op:Hql.Operators.Datatable, prep:bool=True, **kwargs) -> tuple[object, object]:
        from Hql.Expressions.References import NamedReference, Literal
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
                assert isinstance(i, Literal)
                row[keys[idx]] = i.value
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

    def Join(self, op:Hql.Operators.Join, prep:bool=True, **kwargs) -> tuple[object, object]:
        return None, op

    def MvExpand(self, op:Hql.Operators.MvExpand, prep:bool=True, **kwargs) -> tuple[object, object]:
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
            acc, rej = self.compile(i.expr, preprocess=False)
            assert isinstance(acc, str)
            exprs.append(acc)

        if op.limit:
            acc, rej = self.compile(op.limit, preprocess=False)
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

    def Sort(self, op:Hql.Operators.Sort, prep:bool=True, **kwargs) -> tuple[object, object]:
        if prep:
            for i in op.exprs:
                if i.nulls != 'last':
                    return None, op
            return op, None

        exprs = []
        for i in op.exprs:
            field, _ = self.compile(i.expr, preprocess=False)
            assert isinstance(field, str)
            order = '-' if i.order == 'desc' else '+'
            exprs.append(order + field)
        exprs = ', '.join(exprs)

        out = '| sort ' + exprs
        return out, None

    def Rename(self, op:Hql.Operators.Rename, prep:bool=True, **kwargs) -> tuple[object, object]:
        return None, op

    '''
    Expressions
    '''

    def Tabular(self, expr:Hql.Expressions.Expression) -> tuple[Optional[InstructionSet], Optional[Hql.Expressions.Expression]]:
        return None, expr

    def PipeExpression(self, expr:Hql.Expressions.PipeExpression, prep:bool=True, **kwargs) -> tuple[object, object]:
        return None, expr

    def OpParameter(self, expr:Hql.Expressions.OpParameter, prep:bool=True, **kwargs) -> tuple[object, object]:
        return None, expr

    def ToClause(self, expr:Hql.Expressions.ToClause, prep:bool=True, **kwargs) -> tuple[object, object]:
        return None, expr

    def OrderedExpression(self, expr:Hql.Expressions.OrderedExpression, prep:bool=True, **kwargs) -> tuple[object, object]:
        return expr, None

    def ByExpression(self, expr:Hql.Expressions.ByExpression, prep:bool=True, **kwargs) -> tuple[object, object]:
        return expr, None

    def Function(self, expr:Hql.Functions.Function, prep:bool=True, **kwargs) -> tuple[object, object]:
        if prep:
            if expr.name not in self.supported_functions:
                return None, expr

            for i in expr.args:
                acc, rej = self.compile(i, preprocess=False)
                if rej:
                    return None, expr

            return expr, None

        args = []
        for i in expr.args:
            acc, _ = self.compile(i, preprocess=False)
            assert isinstance(acc, str)
            args.append(acc)
        args = ', '.join(args)
        name = self.supported_functions[expr.name]

        return f'{name}({args})', None

    def DotCompositeFunction(self, expr:Hql.Expressions.DotCompositeFunction, prep:bool=True, **kwargs) -> tuple[object, object]:
        return None, expr

    def Equality(self, expr:Hql.Expressions.Equality, prep:bool=True, **kwargs) -> tuple[object, object]:
        from Hql.Expressions.Logic import Equality, NamedReference, Path
        if prep:
            lh, rej = self.compile(expr.lh)
            if rej:
                return None, expr
            assert isinstance(lh, (NamedReference, Path))
            
            rh = []
            for i in expr.rh:
                acc, rej = self.compile(i)
                if rej:
                    return None, expr
                rh.append(acc)
            
            return Equality(lh, expr.op, rh), None

        where = kwargs.get('where', False)

        lh, _ = self.compile(expr.lh, preprocess=False)

        rh = []
        for i in expr.rh:
            acc, _ = self.compile(i, preprocess=False)
            rh.append(acc)

        if where:
            if expr.cs:
                if len(rh) > 1:
                    out = f'{lh} in ('
                    out += ', '.join(rh)
                    out += ')'
                else:
                    out = f'{lh} == {rh[0]}'
            else:
                pairs = []
                for i in rh:
                    pairs.append(f'lower({lh}) == lower({i})')
                out = ' or '.join(pairs)
                out = f'({out})'

            if expr.neq:
                out = 'not ' + out

        else:
            pairs = []
            for i in rh:
                pairs.append(f'{lh}={i}')
            out = ' or '.join(pairs)

            if expr.neq:
                out = f'({out})'
                out = 'NOT ' + out

        return out, None

    def Substring(self, expr:Hql.Expressions.Substring, prep:bool=True, **kwargs) -> tuple[object, object]:
        from Hql.Expressions.Logic import Substring, NamedReference, Path, Expression, StringLiteral

        if prep:
            lh, rej = self.compile(expr.lh)
            if rej:
                return None, expr
            assert isinstance(lh, (NamedReference, Path))
           
            rh = []
            for i in expr.rh:
                acc, rej = self.compile(i)
                if rej:
                    return None, expr
                assert isinstance(acc, Expression)
                rh.append(acc)
            
            return Substring(lh, expr.op, rh), None

        lh, _ = self.compile(expr.lh, preprocess=False)
        assert isinstance(lh, str)

        where = kwargs.get('where', False)

        if where:
            pairs = []
            for i in expr.rh:
                if expr.startswith:
                    value = '^' + i.quote('')
                elif expr.endswith:
                    value = i.quote('') + '$'
                else:
                    value = i.quote('')

                new = StringLiteral(value, verbatim=True)
                acc, _ = self.compile(new, preprocess=False)
                assert isinstance(acc, str)
                pairs.append(f'match({lh}, {acc})')

            if expr.logic_and:
                out = ' AND '.join(pairs)
            else:
                out = ' OR '.join(pairs)

        else:
            pairs = []
            for i in expr.rh:
                if expr.startswith:
                    value = i.quote('') + '*'
                elif expr.endswith:
                    value = '*' + i.quote('')
                else:
                    value = '*' + i.quote('') + '*'

                new = StringLiteral(value, verbatim=True)
                acc, _ = self.compile(new, preprocess=False)
                assert isinstance(acc, str)
                pairs.append(lh + '=' + acc)

            if expr.logic_and:
                out = ' AND '.join(pairs)
            else:
                out = ' OR '.join(pairs)

        return out, None

    def Relational(self, expr:Hql.Expressions.Relational, prep:bool=True, **kwargs) -> tuple[object, object]:
        from Hql.Expressions.Logic import Relational, NamedReference, Path, Expression
        if prep:
            lh, rej = self.compile(expr.lh)
            if rej:
                return None, expr
            assert isinstance(lh, (NamedReference, Path))
            
            rh, rej = self.compile(expr.rh[0])
            if rej:
                return None, expr
            assert isinstance(rh, Expression)
            
            return Relational(lh, expr.op, [rh]), None

        lh, _ = self.compile(expr.lh, preprocess=False)
        assert isinstance(lh, str)
        
        rh, _ = self.compile(expr.rh[0], preprocess=False)
        assert isinstance(rh, str)

        op = expr.op

        return f'{lh} {op} {rh}', None

    def BetweenEquality(self, expr:Hql.Expressions.BetweenEquality, prep:bool=True, **kwargs) -> tuple[object, object]:
        from Hql.Expressions.Logic import BinaryLogic, Relational

        if prep:
            return expr, None

        new = BinaryLogic(
            Relational(expr.lh, '>=', [expr.start]),
            [Relational(expr.lh, '<=', [expr.end])],
            'and'
        )
        acc, _ = self.compile(new, preprocess=False)

        return acc, None

    def BinaryLogic(self, expr:Hql.Expressions.BinaryLogic, prep:bool=True, **kwargs) -> tuple[object, object]:
        from Hql.Expressions.Logic import BinaryLogic
        if prep:
            exprs = [expr.lh] + expr.rh
            accs = []
            rejs = []
            for i in exprs:
                acc, rej = self.compile(i)
                if rej:
                    rejs.append(rej)
                if acc:
                    accs.append(acc)
            
            if expr.bitype == 'or':
                if rejs:
                    return None, expr
                else:
                    return expr, None
            else:
                acc = None
                rej = None
                if accs:
                    acc = BinaryLogic(accs[0], accs[1:], 'and')
                if rejs:
                    rej = BinaryLogic(rejs[0], rejs[1:], 'and')
                return acc, rej
        
        exprs = []
        for i in [expr.lh] + expr.rh:
            acc, _ = self.compile(i, preprocess=False, where=kwargs.get('where', False))
            exprs.append(acc)

        if expr.bitype == 'or':
            out = ' or '.join(exprs)
        else:
            out = ' and '.join(exprs)

        return out, None

    def Not(self, expr:Hql.Expressions.Not, prep:bool=True, **kwargs) -> tuple[object, object]:
        if prep:
            _, rej = self.compile(expr.expr)
            if rej:
                return None, expr
            return expr, None

        inner = self.compile(expr.expr, preprocess=False, where=kwargs.get('where', False))
        out = f'not {inner}'
        return out, None

    def BasicRange(self, expr:Hql.Expressions.BasicRange, prep:bool=True, **kwargs) -> tuple[object, object]:
        return None, expr
        
    def Regex(self, expr:Hql.Expressions.Regex, prep:bool=True, **kwargs) -> tuple[object, object]:
        from Hql.Expressions import Expression, NamedReference, Path, StringLiteral, MultiString

        if prep:
            if expr.g:
                return None, expr

            acc, rej = self.compile(expr.lh)
            if rej:
                return None, expr
            assert isinstance(acc, Expression)
            lh = acc

            acc, rej = self.compile(expr.rh)
            if rej:
                return None, expr
            assert isinstance(acc, Expression)
            rh = acc

            assert isinstance(lh, (NamedReference, Path, StringLiteral))
            expr.lh = lh
            assert isinstance(rh, StringLiteral)
            expr.rh = rh

            return expr, None

        # | where match(dest_mac, "(?sim)00:50:56:ef:8C:19")
        lh, _ = self.compile(expr.lh, preprocess=False)

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

        rh = StringLiteral(flags + expr.rh.quote(''), verbatim=True)
        rh, _ = self.compile(rh, preprocess=False)

        out = f'match({lh}, {rh})'
        return out, None

    def TypeExpression(self, expr:Hql.Expressions.TypeExpression, prep:bool=True, **kwargs) -> tuple[object, object]:
        return None, expr

    def StringLiteral(self, expr:Hql.Expressions.StringLiteral, prep:bool=True, **kwargs) -> tuple[object, object]:
        if prep:
            return expr, None
        return expr.quote('"'), None
    
    def MultiString(self, expr:Hql.Expressions.MultiString, prep:bool=True, **kwargs) -> tuple[object, object]:
        return None, expr

    def Integer(self, expr:Hql.Expressions.Integer, prep:bool=True, **kwargs) -> tuple[object, object]:
        if prep:
            return expr, None
        return expr.value, None

    def IP4(self, expr:Hql.Expressions.IP4, prep:bool=True, **kwargs) -> tuple[object, object]:
        return None, expr

    def Float(self, expr:Hql.Expressions.Float, prep:bool=True, **kwargs) -> tuple[object, object]:
        if prep:
            return expr, None
        return str(expr.value), None

    def Bool(self, expr:Hql.Expressions.Bool, prep:bool=True, **kwargs) -> tuple[object, object]:
        if prep:
            return expr, None
        ret = 'true' if expr.value else 'false'
        return ret, None

    def Multivalue(self, expr:Hql.Expressions.Multivalue, prep:bool=True, **kwargs) -> tuple[object, object]:
        return None, expr

    def Datetime(self, expr:Hql.Expressions.Datetime, prep:bool=True, **kwargs) -> tuple[object, object]:
        from Hql.Expressions.Literals import StringLiteral
        if prep:
            return expr, None
        
        acc = StringLiteral(expr.render(self.time_format), verbatim=True)
        datelit, _ = self.compile(acc, preprocess=False)
        acc = StringLiteral(self.time_format, verbatim=True)
        time_format, _ = self.compile(acc, preprocess=False)

        func = f'strptime({datelit}, {time_format})'
        return func, None 
    
    def NamedReference(self, expr:Hql.Expressions.NamedReference, prep:bool=True, **kwargs) -> tuple[object, object]:
        if prep:
            return expr, None
        return expr.name, None

    def EscapedNamedReference(self, expr:Hql.Expressions.EscapedNamedReference, prep:bool=True, **kwargs) -> tuple[object, object]:
        if prep:
            return expr, None
        return f'{repr(expr.name)}', None

    def Keyword(self, expr:Hql.Expressions.Keyword, prep:bool=True, **kwargs) -> tuple[object, object]:
        return self.NamedReference(expr, prep=prep)

    def Identifier(self, expr:Hql.Expressions.Identifier, prep:bool=True, **kwargs) -> tuple[object, object]:
        return self.NamedReference(expr, prep=prep)

    def Wildcard(self, expr:Hql.Expressions.Wildcard, prep:bool=True, **kwargs) -> tuple[object, object]:
        return self.NamedReference(expr, prep=prep)

    def Path(self, expr:Hql.Expressions.Path, prep:bool=True, **kwargs) -> tuple[object, object]:
        from Hql.Expressions.References import EscapedNamedReference, NamedReference
        from Hql.Expressions.Literals import StringLiteral, NamedExpression
        from Hql.Operators.ProjectRename import ProjectRename
        import random

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

    def NamedExpression(self, expr:Hql.Expressions.NamedExpression, prep:bool=True, **kwargs) -> tuple[object, object]:
        from Hql.Expressions.References import NamedExpression, Expression
        from Hql.Functions import Function

        if prep:
            good_paths = []
            bad_paths = []
            for i in expr.paths:
                acc, rej = self.compile(i)
                if rej:
                    bad_paths.append(rej)
                else:
                    good_paths.append(acc)

            if isinstance(expr.value, Function):
                if expr.value.name not in self.supported_functions:
                    return None, expr
                value = expr.value
            else:
                value, rej = self.compile(expr.value)
                assert isinstance(value, Expression)
                if rej or not good_paths:
                    return None, expr
    
            good = NamedExpression(good_paths, value)
            bad = None
            if bad_paths:
                bad = NamedExpression(bad_paths, value)

            return good, bad

        paths = []
        for i in expr.paths:
            acc, _ = self.compile(i, preprocess=False)
            assert isinstance(acc, str)
            paths.append(acc)

        value, _ = self.compile(expr.value, preprocess=False)
        assert isinstance(value, str)

        exprs = []
        for i in paths:
            exprs.append(f'{i}={value}')

        return ', '.join(exprs), None
