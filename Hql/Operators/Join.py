from __future__ import annotations
from typing import Sequence, Union, Optional, TYPE_CHECKING
from Hql.Operators.Operator import Operator
from Hql.Exceptions import HqlExceptions as hqle

if TYPE_CHECKING:
    from Hql.Expressions import Expression, OpParameter
    from Hql.Expressions.References import Reference
    from Hql.Expressions.Logic import Logic
    from Hql.Data import Data
    from Hql.Compiler import InstructionSet
    from Hql.Context import Context

class Join(Operator):
    """Join the current data with a compiled right-hand expression."""

    def __init__(self, rh:Union[Expression, InstructionSet], on:Sequence[Reference], params:Optional[list[OpParameter]]=None, where:Optional[Logic]=None):
        Operator.__init__(self)
        self.rh = rh
        self.params:list[OpParameter] = params if params else []
        self.on:Sequence[Reference] = on if on else []
        self.where = where

        # default join type
        self.kind = 'inner'
        self.process_params()

        if not self.on:
            raise hqle.QueryException(f'Missing on clause in join: {self.deparse()}')

    def to_dict(self):
        return {
            'id': self.id,
            'type': self.type,
            'kind': self.kind,
            'rh': self.rh.to_dict(),
            'on': [x.to_dict() for x in self.on],
            'where': self.where.to_dict() if self.where else None
        }

    def process_params(self):
        for i in self.params:
            # parser gives a str name, but allow references too
            name = i.name if isinstance(i.name, str) else i.name.str()
            if name == 'kind':
                self.kind = i.value.str()

    # Gets the data resulting from a compiled right side
    def get_right(self, ctx:Context, where:Optional[Logic]) -> Data:
        from Hql.Operators.Where import Where
        from Hql.Compiler import InstructionSet

        if not isinstance(self.rh, InstructionSet):
            raise hqle.CompilerException('Join attempting to get right without compilation, error?')

        rh = self.rh

        # A join where clause acts as a prefilter on the right side
        filters = [x for x in (self.where, where) if x]

        # Add right side filters to a copy, compiling them in pushes ops into
        # the upstream databases so don't touch ours
        if filters:
            rh = InstructionSet(self.copy_rh(), [Where(x) for x in filters])
            rh = rh.recompile(ctx.config)

        return rh.eval(ctx).data

    # Deep copies the right side, sharing HTTP sessions as requests.Session
    # drops subclass attributes when copied
    def copy_rh(self) -> InstructionSet:
        from copy import deepcopy
        # sessions module, requests.Session may be patched in tests
        from requests.sessions import Session
        from Hql.Compiler import InstructionSet

        memo:dict = {}

        def share(obj, seen:set):
            if id(obj) in seen:
                return
            seen.add(id(obj))

            if isinstance(obj, InstructionSet):
                for i in list(obj.upstream) + list(obj.ops):
                    share(i, seen)
                return

            for value in vars(obj).values():
                if isinstance(value, Session):
                    memo[id(value)] = value
                elif isinstance(value, (InstructionSet, Operator)):
                    share(value, seen)

        share(self.rh, set())
        return deepcopy(self.rh, memo)

    # Join kinds where right rows without a matching left key can't affect the
    # output, so the right side can be filtered down to the left keys
    PUSHDOWN_KINDS = ('inner', 'innerunique', 'leftouter', 'leftsemi', 'leftanti', 'rightsemi')

    def gen_optimization(self, data:Data) -> Optional[Logic]:
        from Hql.Operators.Summarize import Summarize
        from Hql.Expressions.Aggregation import ByExpression
        from Hql.Context import Context
        from Hql.Expressions.Logic import Equality, BinaryLogic

        grouped = Summarize([], ByExpression(self.on)).eval(Context(data)).data
        rows = [row for table in grouped for row in table.to_dicts()]

        exprs = []
        for i in rows:
            ands = []
            for j in self.explode_dict(i):
                rh = self.value_from_dict(j)
                # null keys never match in a join
                if rh is None:
                    ands = []
                    break
                lh = self.name_from_dict(j)
                ands.append(Equality(lh, rh))

            if ands:
                exprs.append(BinaryLogic(ands, logic_and=True))

        if not exprs:
            return None
        return BinaryLogic(exprs, logic_and=False)

    def name_from_dict(self, data:dict) -> Reference:
        from Hql.Expressions.References import Path, NamedReference

        path = []
        while True:
            key = list(data.keys())[0]
            path.append(NamedReference(key))
            if not isinstance(data[key], dict):
                break
            data = data[key]
        return Path(path)

    def value_from_dict(self, data:dict):
        from Hql.Expressions.Literals import Integer, StringLiteral, Float, Bool

        while True:
            key = list(data.keys())[0]
            if not isinstance(data[key], dict):
                break
            data = data[key]

        if data[key] is None:
            return None
        # bool is a subclass of int
        if isinstance(data[key], bool):
            return Bool(data[key])
        if isinstance(data[key], int):
            return Integer(data[key])
        if isinstance(data[key], str):
            return StringLiteral(data[key], verbatim=True)
        if isinstance(data[key], float):
            return Float(data[key])
        return StringLiteral(str(data[key]))

    def explode_dict(self, data:dict) -> list:
        out = []
        for i in data:
            if not isinstance(data[i], dict):
                out.append({i: data[i]})
                continue

            up = self.explode_dict(data[i])
            for j in up:
                out.append({i: j})
        return out

    def resolve_on_clause(self):
        ...

    def deparse(self) -> str:
        from Hql.Compiler import InstructionSet
        from Hql.Expressions import PipeExpression

        out = 'join '

        if isinstance(self.rh, InstructionSet):
            out += 'INSTRUCTION_RH'
        else:
            if isinstance(self.rh, PipeExpression):
                out += '(' + self.rh.deparse() + ')'
            else:
                out += self.rh.deparse()

        if self.params:
            out += ' ' + ' '.join([x.deparse() for x in self.params])

        if self.on:
            out += ' on ' + ', '.join([x.deparse() for x in self.on])

        if self.where:
            out += ' where ' + self.where.deparse()

        return out

    def eval(self, ctx:Context):
        self.process_params()

        left = ctx.data

        # Right preserving kinds need the full right side, even with no left
        if self.kind not in self.PUSHDOWN_KINDS:
            right = self.get_right(ctx, None)

        else:
            if not left:
                return ctx
            expr = self.gen_optimization(left)
            right = self.get_right(ctx, expr)

        ctx = ctx.copy()
        ctx.data = left.join(right, self.on, kind=self.kind)
        return ctx
