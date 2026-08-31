from __future__ import annotations
from typing import Optional, Sequence, Union, TYPE_CHECKING
import logging

from Hql.Compiler import Compiler, BranchDescriptor, InstructionSet
from Hql.Exceptions import HqlExceptions as hqle
from Hql.Expressions.References import NamedReference
from Hql.Types.Hql import HqlTypes as hqlt

from Hql.Expressions import References
from Hql.Expressions import Literals
from Hql.Expressions import Logic
from Hql.Expressions import Expression, ToClause, OpParameter, PipeExpression
from Hql.Expressions import PipeExpression
from Hql.Expressions import Aggregation
import Hql.Functions as Functions
import Hql.Expressions.Functions as FuncExprs

from Hql.Database import Database
import Hql.Operators as Operators

from Hql.Query import LetLogicStatement, LetStatement, Statement, QueryStatement

from Hql.Types.Hql import HqlTypes as hqlt

if TYPE_CHECKING:
    from Hql.Query import Query
    from Hql.Config import Config
    from Hql.Context import Context
    from Hql.Hac import Hac
    from Hql.Operators import Operator

_PREPIPE_TYPES = (Functions.Function, Functions.DotCompositeFunction, Database, Operators.Union, References.Reference, InstructionSet)

'''
Hql preprocessor
'compiles' out a set of pure-Hql expressions and operators
Works out preprocessor functions
'''
class HqlCompiler(Compiler):
    """Preprocess HQL into executable instruction sets."""

    def __init__(self, config:Config, query:Optional[Query]=None, hac:Optional[Hac]=None):
        Compiler.__init__(self)
        self.ctx.config = config
        self.root:Optional[InstructionSet] = None
        self.hac:Optional[Hac] = hac

        if query:
            self.Query(query)

    def compile(self, src:Union[Operators.Operator, Expression, Statement, None], prep:bool=True) -> tuple[BranchDescriptor, None]:
        if not src:
            logging.error('Access Hql root via HqlCompiler.root not default compiler')
            raise hqle.CompilerException('Hql compiler with default parameter')
        return self.from_name(src.type)(src)

    def run(self, ctx: Optional[Context] = None) -> Context:
        ctx = ctx if ctx else self.ctx
        if not self.root:
            raise hqle.CompilerException('Attempting to run compiler with None-root')
        ctx.hac = self.hac
        return self.root.eval(ctx)

    def Query(self, query: Hql.Query.Query, prep:bool=True):
        res = None
        for i in query.statements:
            res = self.compile(i)
            if res:
                break
        return res

    def Statement(self, statement: Statement, prep:bool=True) -> Optional[InstructionSet]:
        logging.error("This shouldn't trigger? Compiling Statement directly")
        acc, _ = self.compile(statement.root)
        assert isinstance(acc, InstructionSet)
        return acc

    def QueryStatement(self, statement: QueryStatement, prep:bool=True) -> InstructionSet:
        from Hql.Hac.Sources import Source
        from Hql.Database import Database
        acc, _ = self.compile(statement.root)

        if isinstance(acc, InstructionSet):
            self.root = acc
        elif isinstance(acc, Source):
            self.root = acc.assemble()
        elif isinstance(acc, Database):
            self.root = InstructionSet(acc)
        else:
            raise hqle.CompilerException(f'QueryStatement compiled to {type(acc)} not InstructionSet, mistake?')
        
        return self.root

    def LetStatement(self, statement:LetStatement, prep:bool=True) -> None:
        acc, _ = self.compile(statement.root)

        if not isinstance(acc, InstructionSet):
            acc = acc.get_expr()

        self.ctx.symbol_table[statement.name] = acc
        return None

    def LetLogicStatement(self, statement:LetLogicStatement, prep:bool=True) -> None:
        acc, _ = self.compile(statement.root)

        if not isinstance(acc, InstructionSet):
            acc = acc.get_expr()

        self.ctx.symbol_table[statement.name] = acc
        return None

    def Tabular(self, expr:PrepipeType) -> tuple[Optional[InstructionSet], Optional[Expression]]:
        from Hql.Database import Database, Static
        from Hql.Hac.Sources import Source

        if isinstance(expr, InstructionSet):
            return expr, None

        elif isinstance(expr, Source):
            acc = expr.preprocess(self.ctx)

        elif isinstance(expr, FuncExprs.FuncProto):
            acc, _ = self.compile_expr(expr)
            if not isinstance(acc, _PREPIPE_TYPES):
                raise hqle.CompilerException(f'Tabular function call returned non-prepipe type {type(acc)}')
            return self.Tabular(acc)
        
        elif isinstance(expr, Functions.DotCompositeFunction):
            acc, _ = self.DotCompositeFunction(expr)

        elif isinstance(expr, NamedReference):
            acc = self.ctx.symbol_table[expr]

            if not isinstance(acc, (Database, InstructionSet)):
                acc = self.ctx.get_func('database')([]).eval(self.ctx)
                acc = acc.get_variable(expr)

        elif isinstance(expr, Operators.Range):
            acc, _ = self.Range(expr)
            op = acc.get_op()
            acc = Static(op.eval(self.ctx).data)

        elif isinstance(expr, Operators.Datatable):
            acc, _ = self.Datatable(expr)
            op = acc.get_op()
            acc = Static(op.eval(self.ctx).data)

        elif isinstance(expr, Operators.Union):
            upstream = []
            for i in expr.exprs:
                acc, rej = self.Tabular(i)
                if rej:
                    logging.error(f'   {rej.str()}')
                    logging.error(f'in {expr.str()}')
                    raise hqle.CompilerException('Could not compile Union expression')
                assert acc
                
                if not acc.ops:
                    upstream += acc.upstream
                else:
                    upstream.append(acc)
            
            acc = InstructionSet(upstream=upstream)

        elif isinstance(expr, Database):
            acc = expr

        else:
            logging.error(expr.str())
            logging.error(type(expr))
            raise hqle.CompilerException('Could not compile Tabular expression')

        if isinstance(acc, Source):
            acc = acc.preprocess(self.ctx)

        if isinstance(acc, Database):
            acc = InstructionSet(acc, acc.preamble.pipes)

        if not isinstance(acc, InstructionSet):
            logging.error(acc)
            raise hqle.CompilerException(f'Tabular compilation resulted in {type(acc)} not InstructionSet')

        # Add hac timebound
        if self.hac:
            start, end = self.hac.get_timerange()
            acc, _ = acc.add_timebound(start, end)

        return acc, None

    def PipeExpression(self, expr: PipeExpression, prep:bool=True) -> tuple[Union[InstructionSet, BranchDescriptor], None]:
        prepipe:Optional[InstructionSet] = None

        if expr.prepipe:
            acc, rej = self.Tabular(expr.prepipe)
            if rej:
                return self.compile(rej)
            else:
                prepipe = acc

        if prepipe is None:
            logging.warning('Preprocessing with empty prepipe')
            return InstructionSet([], expr.pipes), None

        new:list[InstructionSet] = []
        for i in prepipe.upstream:
            if isinstance(i, Database):
                i, _ = self.Tabular(i)
            assert i is not None
            new.append(i)
        
        instr = InstructionSet(prepipe, expr.pipes)
            
        return self.InstructionSet(instr), None

    def InstructionSet(self, instr: InstructionSet, prep:bool=True) -> InstructionSet:
        # import json

        # Preprocess all pipes
        pipes:list[BranchDescriptor] = []
        for i in instr.ops:
            acc, _ = self.compile(i)
            pipes.append(acc)

        # for i in pipes:
        #     print(json.dumps(i.get_op().to_dict()))

        # Do basic optimization
        if pipes:
            pipes = self.optimize(pipes)

        # Create groups where data needs to be sync'd
        groups:list[list[BranchDescriptor]] = []
        top = 0
        idx = 0
        for idx, i in enumerate(pipes):
            if i.get_attr('requires_sync'):
                groups.append(pipes[top:idx])
                top = idx
        groups.append(pipes[top:idx+1])

        # Compile first group
        sets = []
        for i in instr.upstream:
            comp = i
            for idx, j in enumerate(groups[0]):
                acc, rej = comp.add_op(j)

                if rej:
                    comp = InstructionSet(comp)
                    comp.add_op(rej)

            if not isinstance(comp, InstructionSet):
                comp = InstructionSet(comp)

            sets.append(comp)

        comp = sets
        for i in groups[1:]:
            comp = InstructionSet(comp)
            for j in i:
                comp.add_op(j.get_op())

        if isinstance(comp, list):
            comp = InstructionSet(comp)

        if len(comp.upstream) == 1 and isinstance(comp.upstream[0], InstructionSet):
            comp.upstream[0].ops += comp.ops
            comp = comp.upstream[0]

        return comp

    '''
    Good god this needs to be improved
    '''
    def optimize(self, ops: Sequence[Union[Operators.Operator, BranchDescriptor]]) -> list[BranchDescriptor]:
        new = []
        for i in ops:
            if isinstance(i, Operators.Operator):
                acc, _ = self.compile(i)
                assert isinstance(acc, BranchDescriptor)
                new.append(acc)
            else:
                new.append(i)
        ops = new
        
        logging.debug(f'Optimizing the following operators:')
        for op in ops:
            logging.debug(f'    {op.get_op().id}: {op.get_op().type}')
        
        optimized = [ops[0]]
        for op in ops[1:]:
            i = -1
            while i >= -len(optimized):
                if not (optimized[i].get_attr('row_dependent') or optimized[i].get_attr('row_mutable')) and op.get_attr('row_reducing'):
                    if isinstance(optimized[i].get_op(), Operators.Take) or isinstance(op.get_op(), Operators.Take):
                        logging.debug("Holding take's location")
                        break

                    if type(optimized[i].get_op()) == type(op.get_op()):
                        break

                    if optimized[i].get_attr('requires_sync') and isinstance(op.get_op(), Operators.Take):
                        break

                    if optimized[i].get_attr('type_casting'):
                        break

                    can_map, mapped = self.apply_map(optimized[i], op)
                    if can_map == 1:
                        op = mapped
                        logging.debug(f'{op.get_op().id} is remapped by {optimized[i].get_op().id}')
                        i -= 1
                        continue

                    if can_map == 2:
                        logging.debug(f'{op.get_op().id} references names provided by {optimized[i].get_op().id}')
                        break

                    logging.debug(f'Can optimize {op.get_op().id} passing {optimized[i].get_op().id}')
                    i -= 1
                    continue

                else:
                    logging.debug(f'As high as we can go for {op.get_op().id}')
                    break
            
            if i == -1:
                optimized.append(op)
            else:
                optimized.insert(i+1, op)
        
        logging.debug('Final optimized set:')
        for op in optimized:
            logging.debug(f'    {op.get_op().id}: {op.get_op().type}')

        return optimized

    def apply_map(self, upstream:BranchDescriptor, integrating:BranchDescriptor) -> tuple[int, BranchDescriptor]:
        from copy import deepcopy

        if not upstream.mapping:
            return 0, integrating

        # Should use this to do allow for more more error checking here
        if isinstance(upstream.op, Operators.Project):
            for i in integrating.references:
                if i not in upstream.mapping and i not in upstream.symmetric and i not in self.ctx.symbol_table:
                    return 2, integrating

        elif type(upstream.op) in (Operators.Extend, Operators.ProjectRename):
            ...
            
        else:
            return 0, integrating
        
        new = deepcopy(self)
        for i in upstream.mapping:
            new.ctx.symbol_table[i] = upstream.mapping[i]

        acc, _ = new.compile(integrating.get_op())
        return 1, acc

    def Where(self, op: Operators.Where, prep:bool=True) -> tuple[BranchDescriptor, None]:
        desc = BranchDescriptor()
        desc.set_attr('row_reducing')

        acc, _ = self.compile(op.expr)
        expr = acc.get_expr()

        if isinstance(expr, Functions.Function) and expr.logic:
            expr = expr.preprocess(self.ctx)
        assert isinstance(expr, Logic.Logic)
        op = Operators.Where(expr, op.parameters)

        desc.op = op
        desc.merge(acc)
        return desc, None

    def Project(self, op: Operators.Project, prep:bool=True) -> tuple[BranchDescriptor, None]:
        from Hql.Operators.Project import Project
        desc = BranchDescriptor()

        exprs = []
        for i in op.exprs:
            acc, _ = self.compile(i)
            if isinstance(acc.get_expr(), NamedReference):
                desc.provides.append(acc.get_expr())
                desc.symmetric.append(acc.get_expr())
            desc.merge(acc)
            exprs.append(acc.get_expr())

        op = Project(exprs)
        desc.op = op
        return desc, None

    def ProjectAway(self, op: Operators.ProjectAway, prep:bool=True) -> tuple[BranchDescriptor, None]:
        acc, _ = self.Project(op)
    
        exprs = []
        for i in acc.get_op().exprs:
            assert isinstance(i, (References.Reference, References.NamedExpression))
            exprs.append(i)

        new = Operators.ProjectAway(exprs)
        acc.op = new

        return acc, _

    def ProjectKeep(self, op: Operators.Project, prep:bool=True) -> tuple[BranchDescriptor, None]:
        acc, _ = self.Project(op)
    
        exprs = []
        for i in acc.get_op().exprs:
            assert isinstance(i, (References.Reference, References.NamedExpression))
            exprs.append(i)

        new = Operators.ProjectKeep(exprs)
        acc.op = new

        return acc, _

    def ProjectReorder(self, op: Operators.Project, prep:bool=True) -> tuple[BranchDescriptor, None]:
        acc, _ = self.Project(op)
    
        exprs = []
        for i in acc.get_op().exprs:
            assert isinstance(i, (References.Reference, References.NamedExpression))
            exprs.append(i)

        new = Operators.ProjectReorder(exprs)
        acc.op = new

        return acc, _

    def ProjectRename(self, op: Operators.ProjectRename, prep:bool=True) -> tuple[BranchDescriptor, None]:
        acc, _ = self.Project(op)
    
        exprs = []
        for i in acc.get_op().exprs:
            assert isinstance(i, (References.Reference, References.NamedExpression))
            exprs.append(i)

        new = Operators.ProjectRename(exprs)
        acc.op = new

        return acc, _

    def Take(self, op: Operators.Take, prep:bool=True) -> tuple[BranchDescriptor, None]:
        from Hql.Operators.Take import Take
        desc = BranchDescriptor()
        desc.set_attr('row_dependent') # take a subset of the above rows
        desc.set_attr('row_reducing')

        acc, _ = self.compile(op.expr)
        desc.merge(acc)
        expr = acc.get_expr()
        assert isinstance(expr, Literals.Integer)

        tables = []
        for i in op.tables:
            acc, _ = self.compile(i)
            desc.merge(acc)
            tables.append(acc.get_expr())

        desc.op = Take(expr, tables)
        return desc, None

    def Count(self, op: Operators.Count, prep:bool=True) -> tuple[BranchDescriptor, None]:
        desc = BranchDescriptor()
        desc.set_attr('row_dependent')
        desc.set_attr('row_mutable')

        expr = None
        if op.name:
            acc, _ = self.compile(op.name)
            desc.merge(acc)
            expr = acc.get_expr()
            assert isinstance(expr, References.NamedReference)

        desc.op = Operators.Count(expr)
        return desc, None

    def Extend(self, op: Operators.Extend, prep:bool=True) -> tuple[BranchDescriptor, None]:
        desc = BranchDescriptor()

        exprs = []
        for i in op.exprs:
            acc, _ = self.compile(i)
            desc.merge(acc)
            exprs.append(acc.get_expr())

        desc.op = Operators.Extend(exprs)
        return desc, None

    def Range(self, op: Operators.Range, prep:bool=True) -> tuple[BranchDescriptor, None]:
        desc = BranchDescriptor()

        acc, _ = self.compile(op.name)
        desc.merge(acc)
        name = acc.get_expr()
        assert isinstance(name, References.NamedReference)
        
        acc, _ = self.compile(op.start)
        desc.merge(acc)
        start = acc.get_expr()
        assert isinstance(start, Expression)
        
        acc, _ = self.compile(op.end)
        desc.merge(acc)
        end = acc.get_expr()
        assert isinstance(end, Expression)

        acc, _ = self.compile(op.step)
        desc.merge(acc)
        step = acc.get_expr()
        assert isinstance(step, Expression)
        
        desc.op = Operators.Range(name, start, end, step)
        return desc, None

    def Top(self, op: Operators.Top, prep:bool=True) -> tuple[BranchDescriptor, None]:
        from Hql.Operators.Top import Top
        from Hql.Expressions.Aggregation import ByExpression
        desc = BranchDescriptor()

        acc, _ = self.compile(op.expr)
        desc.merge(acc)
        expr = acc.get_expr()
        assert isinstance(expr, Literals.Integer)

        acc, _ = self.compile(op.by)
        desc.merge(acc)
        by = acc.get_expr()
        assert isinstance(by, ByExpression)

        desc.op = Top(expr, by)
        return desc, None

    def Unnest(self, op: Operators.Unnest, prep:bool=True) -> tuple[BranchDescriptor, None]:
        from Hql.Operators.Unnest import Unnest
        desc = BranchDescriptor()
        desc.set_attr('row_mutable')

        acc, _ = self.compile(op.field)
        desc.merge(acc)
        field = acc.get_expr()
        assert isinstance(field, Expression)

        tables = []
        for i in op.tables:
            acc, _ = self.compile(i)
            desc.merge(acc)
            tables.append(acc.get_expr())

        desc.op = Unnest(field, tables)
        return desc, None

    def Union(self, op: Operators.Union, prep:bool=True) -> tuple[object, object]:
        from Hql.Operators.Union import Union
        desc = BranchDescriptor()
        desc.set_attr('requires_sync')

        exprs = []
        for i in op.exprs:
            acc, _ = self.compile(i)
            desc.merge(acc)
            exprs.append(acc.get_expr())

        name = None
        if op.name:
            acc, _ = self.compile(op.name)
            acc.provides = acc.references
            acc.references = []
            desc.merge(acc)
            name = acc.get_expr()
            assert isinstance(name, Expression)
        
        desc.op = Union(exprs, name=name)
        return desc, None

    def Summarize(self, op: Operators.Summarize, prep:bool=True) -> tuple[BranchDescriptor, None]:
        desc = BranchDescriptor()
        desc.set_attr('row_dependent')
        desc.set_attr('requires_sync')

        exprs = []
        for i in op.aggregate_exprs:
            acc, _ = self.compile(i)
            desc.merge(acc)
            exprs.append(acc.get_expr())

        acc, _ = self.ByExpression(op.by_expr)
        desc.merge(acc)
        by_expr = acc.get_expr()

        # Mostly done to shut my linter up
        if not isinstance(by_expr, Aggregation.ByExpression):
            raise hqle.CompilerException(f'ByExpression returned non-ByExpression expr type {type(by_expr)}')

        desc.op = Operators.Summarize(exprs, by_expr)
        return desc, None

    def Datatable(self, op: Operators.Datatable, prep:bool=True) -> tuple[BranchDescriptor, None]:
        desc = BranchDescriptor()

        schema = []
        for i in op.schema:
            acc, _ = self.compile(i[0])
            desc.merge(acc)
            name = acc.get_expr()

            acc, _ = self.compile(i[1])
            desc.merge(acc)
            t = acc.get_expr()
            
            schema.append([name, t])

        values = []
        for i in op.values:
            acc, _ = self.compile(i)
            desc.merge(acc)
            values.append(acc.get_expr())

        name = None
        if op.name:
            acc, _ = self.compile(op.name)
            desc.merge(acc)
            name = acc.get_expr()
            assert isinstance(name, References.NamedReference)

        desc.op = Operators.Datatable(schema, values, name=name)
        return desc, None

    def Join(self, op: Operators.Join, prep:bool=True) -> tuple[BranchDescriptor, None]:
        from Hql.Expressions import PipeExpression
        desc = BranchDescriptor()

        # The case of recompiling a compiled join
        if isinstance(op.rh, InstructionSet):
            rh = op.rh
            desc.join_attrs = rh.attrs

        elif isinstance(op.rh, PipeExpression):
            acc, _ = self.compile(op.rh)
            desc.join_attrs = acc.attrs
            rh = acc

        else:
            acc, _ = self.Tabular(op.rh)
            assert acc != None
            desc.join_attrs = acc.attrs
            rh = acc
        assert isinstance(rh, InstructionSet)

        params = []
        for i in op.params:
            acc, _ = self.compile(i)
            desc.merge(acc)
            params.append(acc.get_expr())
        
        on = []
        for i in op.on:
            acc, _ = self.compile(i)
            desc.merge(acc)
            on.append(acc.get_expr())

        where = None
        if op.where:
            acc, _ = self.compile(op.where)
            desc.merge(acc)
            where = acc.get_expr()
            assert isinstance(where, Logic.Logic)

        desc.op = Operators.Join(rh, params=params, on=on, where=where)
        return desc, None

    def MvExpand(self, op: Operators.MvExpand, prep:bool=True) -> tuple[BranchDescriptor, None]:
        from Hql.Expressions.Literals import Integer
        desc = BranchDescriptor()
        desc.set_attr('row_mutable')

        exprs = []
        for i in op.exprs:
            acc, _ = self.compile(i)
            desc.merge(acc)
            exprs.append(acc.get_expr())
        
        limit = None
        if op.limit:
            acc, _ = self.compile(op.limit)
            desc.merge(acc)
            limit = acc.get_expr()
            assert isinstance(limit, Integer)

        desc.op = Operators.MvExpand(exprs, limit)
        return desc, None

    def Sort(self, op: Operators.Sort, prep:bool=True) -> tuple[BranchDescriptor, None]:
        from Hql.Operators.Sort import Sort
        desc = BranchDescriptor()
        desc.set_attr('row_dependent')

        exprs = []
        for i in op.exprs:
            acc, _ = self.compile(i)
            desc.merge(acc)
            exprs.append(acc.get_expr())

        desc.op = Sort(exprs)
        return desc, None

    def Rename(self, op: Operators.Rename, prep:bool=True) -> tuple[BranchDescriptor, None]:
        desc = BranchDescriptor()
        desc.set_attr('table_mutable')

        exprs = []
        for i in op.exprs:
            acc, _ = self.compile(i)
            desc.merge(acc)
            exprs.append(acc.get_expr())

        desc.op = Operators.Rename(exprs)
        return desc, None
    
    def OpParameter(self, expr: OpParameter, prep:bool=True) -> tuple[BranchDescriptor, None]:
        desc = BranchDescriptor()

        acc, _ = self.compile(expr.value)
        desc.merge(acc)
        value = acc.get_expr()
        assert isinstance(value, Expression)

        desc.expr = OpParameter(expr.name, value)
        return desc, None

    def ToClause(self, expr:ToClause, prep:bool=True) -> tuple[BranchDescriptor, None]:
        from Hql.Types.Hql import HqlTypes as hqlt
        desc = BranchDescriptor()

        if isinstance(expr.to, hqlt.HqlType):
            desc.set_attr('type_casting')
            desc.set_attr('types', expr.to)
            to = expr.to
        
        else:
            acc, _ = self.compile(expr.to)
            desc.merge(acc)
            to = acc.get_expr()

        assert isinstance(to, hqlt.HqlType)

        acc, _ = self.compile(expr.expr)
        desc.merge(acc)
        name = acc.get_expr()
        assert isinstance(name, NamedReference)
    
        desc.expr = ToClause(name, to)
        return desc, None

    def OrderedExpression(self, expr:Aggregation.OrderedExpression, prep:bool=True) -> tuple[BranchDescriptor, None]:
        from Hql.Expressions.Aggregation import OrderedExpression
        desc = BranchDescriptor()
        desc.set_attr('null_ordering')
        desc.set_attr('ordering')

        acc, _ = self.compile(expr.expr)
        desc.merge(acc)
        ordered_expr = acc.get_expr()
        assert isinstance(ordered_expr, Expression)

        desc.expr = OrderedExpression(ordered_expr, order=expr.order, nulls=expr.nulls)
        return desc, None

    def ByExpression(self, expr:Aggregation.ByExpression, prep:bool=True) -> tuple[BranchDescriptor, None]:
        desc = BranchDescriptor()
        desc.set_attr('aggregation')

        by_exprs = []
        for i in expr.exprs:
            acc, _ = self.compile(i)
            desc.merge(acc)
            by_exprs.append(acc.get_expr())

        desc.expr = Aggregation.ByExpression(by_exprs)
        return desc, None

    def Function(self, expr: Functions.Function, prep:bool=True) -> tuple[BranchDescriptor, None]:
        from Hql.Functions import typecasting

        desc = BranchDescriptor()
        desc.set_attr('functions', expr.name)

        args = []
        for i in expr.args:
            acc, _ = self.compile(i)
            desc.merge(acc)
            args.append(acc.get_expr())

        if isinstance(expr, typecasting.Typecast):
            desc.set_attr('type_casting')

        expr.args = args
        desc.expr = expr

        return desc, None

    def FuncExpr(self, expr:FuncExprs.FuncExpr, prep:bool=True) -> tuple[BranchDescriptor, None]:
        func_expr = expr.preprocess(self.ctx)
        return self.Function(func_expr)

    def DotFuncExpr(self, expr:FuncExprs.DotFuncExpr, prep:bool=True) -> tuple[BranchDescriptor, None]:
        func_expr = expr.preprocess(self.ctx)
        
        if isinstance(func_expr, Functions.Function):
            return self.Function(func_expr)
        else:
            return self.DotCompositeFunction(func_expr)

    def ReceiverFuncExpr(self, expr:FuncExprs.ReceiverFuncExpr, prep:bool=True) -> tuple[object, None]:
        from Hql.Database import Database
        from Hql.Expressions.__proto__ import Expression
        from Hql.Expressions.Functions import FuncExpr
        from Hql.Expressions.References import NamedReference
        from Hql.Operators.Operator import Operator

        desc = BranchDescriptor()

        acc, _ = self.compile(expr.call)
        desc.merge(acc)
        call = acc.get_expr()
        assert isinstance(call, Functions.Function)

        acc, _ = self.compile(expr.receiver)
        desc.merge(acc)
        receiver = acc.get_expr()

        if isinstance(receiver, Functions.Function):
            dotfunc = Functions.DotCompositeFunction([receiver, call])
            assert isinstance(dotfunc, Functions.DotCompositeFunction)
            return self.DotCompositeFunction(dotfunc)

        acc, _ = self.compile(expr.call.name)
        desc.merge(acc)
        name = acc.get_expr()
        assert isinstance(name, NamedReference)

        ############################################

        args = []
        for i in expr.call.args:
            acc, _ = self.compile(i)
            desc.merge(acc)
            args.append(acc.get_expr())

        desc.set_attr('functions', name.str())
        func = FuncExpr(name, args).preprocess(self.ctx)
        assert isinstance(func, Function)
        func.preprocess(self.ctx, receiver=receiver)
        res = func.eval(self.ctx, receiver=receiver)

        if isinstance(res, (InstructionSet, Database)):
            return res, None

        if isinstance(res, (Expression, Operator)):
            return self.compile(res)

        desc.expr = res
        return desc, None

    def DotCompositeFunction(self, expr:Functions.DotCompositeFunction, prep:bool=True) -> tuple[BranchDescriptor, None]:
        from Hql.Database import Database
        desc = BranchDescriptor()

        funcs:list[Functions.Function] = []
        for i in expr.funcs:
            if isinstance(i, Functions.Function):
                funcs.append(i)
                continue

            acc, _ = self.FuncExpr(i)
            desc.merge(acc)
            acc = acc.get_expr()
            assert isinstance(acc, Functions.Function)
            funcs.append(acc)

        if prep:
            res = Functions.DotCompositeFunction(funcs).eval(self.ctx)
            if isinstance(res, (Expression, Operators.Operator)) and not isinstance(res, Database):
                return self.compile(res)
            return res, None

        if len(funcs) > 1:
            desc.set_attr('dot_functions')
            desc.expr = Functions.DotCompositeFunction(funcs)
        else:
            # Breakdown a dot function to a normal function
            desc.expr = funcs[0]

        return desc, None

    def Equality(self, expr:Logic.Equality, prep:bool=True) -> tuple[BranchDescriptor, None]:
        desc = BranchDescriptor()
        desc.set_attr('case_insensitive_compare', not expr.cs)
        desc.set_attr('case_sensitive_compare', expr.cs)

        acc, _ = self.compile(expr.lh)
        desc.merge(acc)
        lh = acc.get_expr()
        assert isinstance(lh, References.Reference)

        rh = []
        for i in expr.rh:
            acc, _ = self.compile(i)
            desc.merge(acc)
            rh.append(acc.get_expr())

        desc.expr = Logic.Equality(lh, rh, cs=expr.cs, neq=expr.neq)
        return desc, None

    def Substring(self, expr:Logic.Substring, prep:bool=True) -> tuple[BranchDescriptor, None]:
        from Hql.Expressions.Logic import Substring
        desc = BranchDescriptor()
        desc.set_attr('case_insensitive_compare', not expr.cs)
        desc.set_attr('case_sensitive_compare', expr.cs)
        desc.set_attr('term_matching', expr.term)
        desc.set_attr('substring_matching')

        acc, _ = self.compile(expr.lh)
        desc.merge(acc)
        lh = acc.get_expr()
        assert isinstance(lh, References.Reference)

        rh = []
        for i in expr.rh:
            acc, _ = self.compile(i)
            desc.merge(acc)
            rh.append(acc.get_expr())

        expr.lh = lh
        expr.rh = rh
        desc.expr = expr
        return desc, None

    def Relational(self, expr:Logic.Relational, prep:bool=True) -> tuple[BranchDescriptor, None]:
        desc = BranchDescriptor()

        acc, _ = self.compile(expr.lh)
        desc.merge(acc)
        lh = acc.get_expr()
        assert isinstance(lh, References.Reference)

        acc, _ = self.compile(expr.rh)
        desc.merge(acc)
        rh = acc.get_expr()
        assert isinstance(rh, Expression)

        desc.expr = Logic.Relational(lh, rh, expr.gt, expr.eq)
        return desc, None

    def BetweenEquality(self, expr:Logic.BetweenEquality, prep:bool=True) -> tuple[BranchDescriptor, None]:
        desc = BranchDescriptor()
        desc.set_attr('range_compare')

        acc, _ = self.compile(expr.lh)
        desc.merge(acc)
        lh = acc.get_expr()
        assert isinstance(lh, References.Reference)

        acc, _ = self.compile(expr.start)
        desc.merge(acc)
        start = acc.get_expr()
        assert isinstance(start, Literals.Literal)
        
        acc, _ = self.compile(expr.end)
        desc.merge(acc)
        end = acc.get_expr()
        assert isinstance(end, Literals.Literal)

        desc.expr = Logic.BetweenEquality(lh, start, end, expr.neq)
        return desc, None

    def BinaryLogic(self, expr:Logic.BinaryLogic, prep:bool=True) -> tuple[BranchDescriptor, None]:
        desc = BranchDescriptor()

        exprs = []
        for i in expr.exprs:
            acc, _ = self.compile(i)
            exprs.append(acc.get_expr())
            desc.merge(acc)

        desc.expr = Logic.BinaryLogic(exprs, expr.logic_and)
        return desc, None

    def Not(self, expr: Logic.Not, prep:bool=True) -> tuple[BranchDescriptor, None]:
        desc = BranchDescriptor()

        acc, _ = self.compile(expr.expr)
        desc.merge(acc)
        inner = acc.get_expr()
        assert isinstance(inner, Logic.Logic)
        
        desc.expr = Logic.Not(inner)
        return desc, None

    def BasicRange(self, expr:Logic.BasicRange, prep:bool=True) -> tuple[BranchDescriptor, None]:
        desc = BranchDescriptor()
        desc.set_attr('range_compare')

        acc, _ = self.compile(expr.start)
        desc.merge(acc)
        start = acc.get_expr()
        assert isinstance(start, Literals.Literal)
        
        acc, _ = self.compile(expr.end)
        desc.merge(acc)
        end = acc.get_expr()
        assert isinstance(end, Literals.Literal)

        desc.expr = Logic.BasicRange(start, end)
        return desc, None

    def Regex(self, expr:Hql.Expressions.Regex, prep:bool=True) -> tuple[BranchDescriptor, None]:
        desc = BranchDescriptor()
        desc.set_attr('regex_matching')
        desc.set_attr('regex_insensitive', expr.i)
        desc.set_attr('regex_multiline', expr.m)
        desc.set_attr('regex_dotall', expr.s)
        desc.set_attr('regex_global', expr.g)

        acc, _ = self.compile(expr.lh)
        desc.merge(acc)
        lh = acc.get_expr()
        assert isinstance(lh, References.Reference)
        
        acc, _ = self.compile(expr.rh)
        desc.merge(acc)
        rh = acc.get_expr()
        assert isinstance(rh, Literals.StringLiteral)

        desc.expr = Logic.Regex(lh, rh, expr.i, expr.m, expr.s, expr.g)
        return desc, None
    
    def TypeExpression(self, expr:Literals.TypeExpression, prep:bool=True) -> tuple[BranchDescriptor, None]:
        desc = BranchDescriptor()
        desc.set_attr('types', expr.eval(self.ctx))
        desc.expr = expr
        
        return desc, None

    def StringLiteral(self, expr:Literals.StringLiteral, prep:bool=True) -> tuple[BranchDescriptor, None]:
        desc = BranchDescriptor()
        desc.set_attr('types', hqlt.string())
        desc.expr = expr

        return desc, None
    
    def MultiString(self, expr:Literals.MultiString, prep:bool=True) -> tuple[BranchDescriptor, None]:
        desc = BranchDescriptor()

        val = ''
        for i in expr.strlits:
            val += i.quote('')

        desc.set_attr('types', hqlt.string())
        desc.expr = Literals.StringLiteral(val)
        return desc, None

    def Integer(self, expr:Literals.Integer, prep:bool=True) -> tuple[BranchDescriptor, None]:
        desc = BranchDescriptor()
        desc.set_attr('types', hqlt.int())
        desc.expr = expr

        return desc, None

    def IP4(self, expr:Literals.IP4, prep:bool=True) -> tuple[BranchDescriptor, None]:
        desc = BranchDescriptor()
        desc.set_attr('types', hqlt.ip4())
        desc.expr = expr

        return desc, None

    def Float(self, expr:Literals.Float, prep:bool=True) -> tuple[BranchDescriptor, None]:
        desc = BranchDescriptor()
        desc.set_attr('types', hqlt.float())
        desc.expr = expr

        return desc, None

    def Bool(self, expr:Literals.Bool, prep:bool=True) -> tuple[BranchDescriptor, None]:
        desc = BranchDescriptor()
        desc.set_attr('types', hqlt.bool())
        desc.expr = expr

        return desc, None

    def Datetime(self, expr: Literals.Datetime, prep:bool=True) -> tuple[BranchDescriptor, object]:
        desc = BranchDescriptor()
        desc.set_attr('types', hqlt.datetime())
        desc.expr = expr

        return desc, None
    
    def NamedReference(self, expr:References.NamedReference, prep:bool=True) -> tuple[BranchDescriptor, None]:
        from Hql.Database import Database

        desc = BranchDescriptor()

        if expr in self.ctx.symbol_table and expr != self.ctx.symbol_table[expr]:
            res = self.ctx.symbol_table[expr]
            # not needed?
            if not isinstance(res, (PipeExpression, Database, InstructionSet)):
                acc, _ = self.compile(res)
                desc.expr = acc.get_expr()
                desc.merge(desc)
                return desc, None

        desc.expr = expr
        desc.references = [expr]
        return desc, None

    def EscapedNamedReference(self, expr:References.EscapedNamedReference, prep:bool=True) -> tuple[BranchDescriptor, None]:
        acc, _ = self.NamedReference(expr)
        acc.set_attr('complex_names')
        return acc, None

    def Wildcard(self, expr:References.Wildcard, prep:bool=True) -> tuple[BranchDescriptor, None]:
        acc, _ = self.NamedReference(expr)
        acc.set_attr('wildcards')
        return acc, None

    def Path(self, expr:References.Path, prep:bool=True) -> tuple[BranchDescriptor, None]:
        from Hql.Database import Database

        desc = BranchDescriptor()

        if expr in self.ctx.symbol_table:
            res = self.ctx.symbol_table[expr]

            if not isinstance(res, (PipeExpression, Database, InstructionSet)):
                acc, _ = self.compile(res)
                desc.expr = acc.get_expr()
                desc.merge(desc)
                return desc, None
        
        desc.set_attr('nested_objects')
        
        path = []
        for i in expr.path:
            acc, _ = self.compile(i)
            desc.merge(acc)
            path.append(i)

        desc.expr = References.Path(path)
        desc.references = [desc.expr]
        return desc, None

    def NamedExpression(self, expr:Hql.Expressions.NamedExpression, prep:bool=True) -> tuple[BranchDescriptor, None]:
        desc = BranchDescriptor()
        desc.set_attr('assignment')

        acc, _ = self.compile(expr.value)
        desc.merge(acc)
        value = acc.get_expr()

        paths = []
        for i in expr.paths:
            acc, _ = self.compile(i)
            desc.merge(acc)
            dest = acc.get_expr()
            assert isinstance(dest, References.Reference)

            if isinstance(value, References.Reference):
                desc.add_mapping(dest, value)
                desc.references.append(value)

            desc.provides.append(dest)
            paths.append(dest)

        desc.expr = References.NamedExpression(paths, value)
        return desc, None
