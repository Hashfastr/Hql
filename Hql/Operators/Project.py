from __future__ import annotations
from typing import Sequence, Union, TYPE_CHECKING
from Hql.Operators.Operator import Operator

if TYPE_CHECKING:
    from Hql.Expressions import Expression
    from Hql.Expressions.References import Reference, NamedExpression
    from Hql.Context import Context
    from Hql.Data import Table

# Project my beloved
# Defines a number of fields to be kept in the output following this operator.
#
# {"test1":"val","test2":"val","test3":"val","test4":"val","test5":"val"}
# | project test1, test3, test5
#
# Would result in
#
# {"test1":"val","test3":"val","test5":"val"}
# https://learn.microsoft.com/en-us/kusto/query/project-operator
class Project(Operator):
    """Select or compute fields for the output data."""

    _exprs: Sequence[Expression]

    def __init__(self, exprs:Sequence[Expression]):
        Operator.__init__(self)
        self.exprs = exprs
        self.optok = 'project'

    @property
    def exprs(self) -> Sequence[Expression]:
        return self._exprs

    @exprs.setter
    def exprs(self, value:Sequence[Expression]) -> None:
        from Hql.Expressions import Expression
        from Hql.Exceptions import HqlExceptions as hqle

        new:list[Expression] = []
        for v in value:
            if not isinstance(v, Expression):
                raise hqle.CompilerException('Setting Project exprs to non-Expression')
            new.append(v)
        self._exprs = new

    def deparse(self) -> str:
        out = self.optok

        if self.exprs:
            out += ' ' + ', '.join(x.deparse() for x in self.exprs)

        return out

    def eval(self, ctx:Context) -> Context:
        from Hql.Data import Data
        from Hql.Expressions.References import NamedExpression

        datasets = []
        for i in self.exprs:
            if isinstance(i, NamedExpression):
                datasets.append(i.eval(ctx, insert=False, unnest=False).data)
            else:
                datasets.append(i.eval(ctx).data)

        ctx.data = Data.merge(datasets)
        return ctx

# Identical to Project, keeping now for compat
class ProjectKeep(Project):
    """Retain fields using the project-keep syntax."""

    def __init__(self, exprs: Sequence[Union[Reference, NamedExpression]]):
        super().__init__(exprs)
        self.optok = 'project-keep'

class ProjectAway(Project):
    """Remove the selected fields from the output data."""

    def __init__(self, exprs: Sequence[Union[Reference, NamedExpression]]):
        super().__init__(exprs)
        self.optok = 'project-away'

    def eval(self, ctx:Context) -> Context:
        ctx = ctx.copy()

        paths = [i.list() for i in self.exprs]
        ctx.data = ctx.data.drop_many(paths)
        return ctx

class ProjectReorder(Project):
    """Move selected fields to the front of the output data."""

    def __init__(self, exprs: Sequence[Union[Reference, NamedExpression]]):
        super().__init__(exprs)
        self.optok = 'project-reorder'

    '''
    Gonna take out the specific bits and move them to the front
    '''
    def eval(self, ctx:Context) -> Context:
        from Hql.Data import Data
        from Hql.Expressions.References import NamedExpression

        ctx = ctx.copy()
        right = ctx.data

        left = super().eval(ctx).data

        paths = []
        for expr in self.exprs:
            if isinstance(expr, NamedExpression):
                paths += [x.list() for x in expr.paths]
            else:
                paths.append(expr.list())

        for path in paths:
            right = right.drop(path)

        ctx.data = Data.merge([left, right])
        return ctx

class ProjectRename(Project):
    """Rename selected fields while preserving their values and types."""

    def __init__(self, exprs: Sequence[Union[Reference, NamedExpression]]):
        super().__init__(exprs)
        self.optok = 'project-rename'

        for i in exprs:
            assert isinstance(i.value, Reference)

    def rename(self, table:Table):
        from Hql.Data import Schema

        for i in self.exprs:
            assert isinstance(i, NamedExpression)
            assert isinstance(i.value, Reference)

            value = table.get_value(i.value)
            vtype = table.schema.get_type(i.value)
            if isinstance(vtype, Schema):
                vtype = vtype.schema
            table.drop(i.value)

            for j in i.paths:
                table.insert(j, value, vtype)

        return table

    def eval(self, ctx:Context) -> Context:
        for table in ctx.data:
            self.rename(table)

        return ctx
