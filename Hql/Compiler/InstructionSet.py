from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Union, Sequence
import logging
import time
import json
import datetime
from Hql.Exceptions import HqlExceptions as hqle
import polars.exceptions as ple
    
from Hql.Context import Context

if TYPE_CHECKING:
    from Hql.Operators.Operator import Operator
    from Hql.Database import Database
    from Hql.Compiler import BranchDescriptor
    from Hql.Query import Mapping
    from Hql.Config import Config

class InstructionSet():
    """Execute upstream data sources followed by local pipeline operators."""

    def __init__(self, upstream:Union[Database, InstructionSet, Sequence[Union[Database, InstructionSet]]], operators:list[Operator] | None=None) -> None:
        import random
        from Hql.Compiler import InstructionSet

        self._upstream = []
        self._ops = []
        
        self.id = '%08x' % random.getrandbits(32)
        self.attrs = dict()

        self.upstream = upstream
        self.ops = operators

        self.maps:list[Mapping] = []

        if len(self.upstream) == 1 and isinstance(self.upstream[0], InstructionSet):
            self.ops = self.upstream[0].ops + self.ops
            self.upstream = self.upstream[0].upstream

    @property
    def upstream(self) -> Sequence[Union[Database, InstructionSet]]:
        return self._upstream

    @upstream.setter
    def upstream(self, val:Union[Database, InstructionSet, Sequence[Union[Database, InstructionSet]]]):
        from Hql.Database import Database

        if not isinstance(val, Sequence):
            val = [val]

        if not val:
            raise hqle.CompilerException('InstructionSet given empty upstream')

        for i in val:
            logging.debug(f'{self.id}: Added upstream {i}')
            if not isinstance(i, (Database, InstructionSet)):
                raise hqle.CompilerException(f'InstructionSet upstream not given Database or InstructionSet, got: {type(i)}')

        self._upstream = val

    @property
    def ops(self) -> list[Operator]:
        return self._ops

    @ops.setter
    def ops(self, val:Optional[list[Operator]]=None):
        from Hql.Operators import Operator

        val = val if val else []

        for i in val:
            logging.debug(f'{self.id}: Added operator {i}')
            if not isinstance(i, Operator):
                raise hqle.CompilerException(f'InstructionSet given non-Operator as in operators, got: {type(i)}')

        self._ops = val

    def preprocess(self, ctx:Context) -> Union[Database, InstructionSet]:
        new = self.recompile(ctx.config)
        if len(new.upstream) == 1 and not new.ops:
            return new.upstream[0]
        return new

    def is_empty(self) -> bool:
        return not (self.upstream or self.ops)

    def to_dict(self):
        from Hql.Operators.Join import Join

        ops = []
        for i in self.ops:
            if isinstance(i, Join):
                op = {
                    'id': i.id,
                    'type': i.type,
                    'deparse': i.deparse(),
                    'rh': i.rh.to_dict()
                }
                ops.append(op)
                continue

            op = i.to_dict()
            op = {
                'id': op.get('id', '????'),
                'type': op.get('type'),
                'deparse': i.deparse()
            }
            ops.append(op)

        return {
            'id': self.id,
            'attrs': self.attrs,
            'upstream': [x.to_dict() for x in self.upstream],
            'ops': ops,
        }

    def add_op(self, op:Union[BranchDescriptor, Operator]) -> tuple[Union[Operator, None], Union[Operator, None]]:
        from Hql.Compiler import BranchDescriptor
        from Hql.Operators import Map
        from Hql.Query import Mapping

        if isinstance(op, BranchDescriptor):
            op = op.get_op()

        # Map is a directive for the operators added after it, not an operation
        if isinstance(op, Map):
            for i in op.maps:
                if not isinstance(i, Mapping):
                    raise hqle.CompilerException(f'InstructionSet given unresolved mapping {i.deparse()}')
                if i not in self.maps:
                    self.maps.append(i)
            return None, None

        if self.maps:
            op = self.map_op(op)

        self.ops.append(op)
        return None, None

    '''
    Recompiles an operator with the mappings in the symbol table, renaming
    the query's names to the data's names.

    EventID == 4624 -> event.id == 4624
    '''
    def map_op(self, op:Operator) -> Operator:
        from copy import deepcopy
        from Hql.Compiler import HqlCompiler
        from Hql.Config import Config

        compiler = HqlCompiler(Config())

        multi = []
        for mapping in self.maps:
            for src in mapping:
                dests = mapping[src]
                if len(dests) == 1:
                    compiler.ctx.symbol_table[src] = dests[0]
                else:
                    multi.append(src)

        # Copy as compilation can modify expressions in place
        acc, _ = compiler.compile(deepcopy(op))

        for i in multi:
            if i in acc.references or i in acc.provides:
                raise hqle.CompilerException(f'{i.deparse()} maps to multiple fields, not supported in {op.type} yet')

        return acc.get_op()

    '''
    Appends a rename of the data's names back to the query's names, then
    clears the mappings as the following operators see the query's names.

    event.id -> EventID
    '''
    def unmap(self) -> None:
        from Hql.Operators import ProjectRename
        from Hql.Expressions.References import NamedExpression

        exprs = []
        for mapping in self.maps:
            for src in mapping:
                for dest in mapping[src]:
                    exprs.append(NamedExpression([src], dest))

        if exprs:
            self.ops.append(ProjectRename(exprs))

        self.maps = []

    def add_timebound(self, start:datetime.datetime, end:datetime.datetime) -> tuple[InstructionSet, None]:
        bounded = []
        for i in self.upstream:
            acc, rej = i.add_timebound(start, end)
            if rej:
                acc = InstructionSet(acc, operators=[rej])
            bounded.append(acc)

        # print(self.ops)

        return InstructionSet(bounded, operators=self.ops), None

    # def flatten(self) -> InstructionSet:
    #     new = []
    #     for i in self.upstream:
    #         if isinstance(i, InstructionSet):
    #             print(i)
    #             new.append(i.flatten())
    #         else:
    #             new.append(i)
    #
    #     if len(new) == 1 and isinstance(new[0], InstructionSet):
    #         new[0].ops += self.ops
    #         return new[0]
    #
    #     elif len(new) == 1:
    #         ops = []
    #         for idx, i in enumerate(self.ops):
    #             acc, rej = new[0].add_op(i)
    #             if rej:
    #                 ops = self.ops[idx:]
    #                 break
    #         self.ops = ops
    #         self.upstream = new
    #
    #     else:
    #         self.upstream = new
    #
    #     return self

    def recompile(self, config:Config) -> InstructionSet:
        from Hql.Compiler import HqlCompiler
        return HqlCompiler(config).InstructionSet(self)

    def exec(self, inst:Union[Database, Operator], ctx:Context) -> Context:
        logging.debug(f'Executing {inst.type} - {inst.id}')
        start = time.perf_counter()

        try:
            ctx = inst.eval(ctx)
        except ple.ColumnNotFoundError:
            # disappointment, that filter wasn't for it
            # clear each table
            for i in ctx.data:
                i.truncate(0)

        end = time.perf_counter()
        logging.debug(f'{inst.id} - {end - start}')

        return ctx

    def render(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    def eval(self, ctx:Context) -> Context:
        from Hql.Threading import InstructionPool

        logging.debug(f'Starting InstructionSet {self.id}')
        start = time.perf_counter()

        # print(self.upstream)

        pool = InstructionPool(auto_run=False)
        for i in self.upstream:
            # A child cache per upstream, merged back into ours when it finishes
            pool.add_instruction(i, ctx.fork())

        pool.start()

        sets = []
        while not pool.is_idle():
            time.sleep(0.1)
            completed = pool.get_completed()
            sets += [x.output for x in completed]

        if None in sets:
            logging.error(f'Failed upstreams: {[x.id for x in self.upstream]}')
            raise hqle.CompilerException('One or more upstream instruction sets failed to execute')

        ctx = Context.merge(sets, merge_rows=False)

        for i in self.ops:
            ctx = self.exec(i, ctx)

        end = time.perf_counter()
        logging.debug(f'InstructionSet {self.id} - {end - start}')

        return ctx
