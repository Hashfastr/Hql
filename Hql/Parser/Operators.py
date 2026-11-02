from __future__ import annotations
from .grammar.HqlVisitor import HqlVisitor
from .grammar.HqlParser import HqlParser

from Hql.Exceptions import HqlExceptions as hqle

class Operators(HqlVisitor):
    def __init__(self):
        pass
    
    def visitStrictQueryOperatorParameter(self, ctx: HqlParser.StrictQueryOperatorParameterContext):
        from Hql.Expressions import OpParameter

        if ctx.NameToken == None:
            raise hqle.ParseException('QueryParameter NameToken is None!', ctx)

        name = ctx.NameToken.text
        value = self.visit(ctx.NameValue) if ctx.NameValue else self.visit(ctx.LiteralValue)
        
        return OpParameter(name, value)

    def visitRelaxedQueryOperatorParameter(self, ctx: HqlParser.RelaxedQueryOperatorParameterContext):
        from Hql.Expressions import OpParameter

        if ctx.NameToken == None:
            raise hqle.ParseException('QueryParameter NameToken is None!', ctx)

        name = ctx.NameToken.text

        if ctx.NameValue:
            value = self.visit(ctx.NameValue)
        else:
            value = self.visit(ctx.LiteralValue)
        
        return OpParameter(name, value)

    def visitRenameOperator(self, ctx: HqlParser.RenameOperatorContext):
        from Hql.Operators.Rename import Rename
        exprs = [self.visit(x) for x in ctx.Expressions]
        return Rename(exprs)

    def visitMapOperator(self, ctx: HqlParser.MapOperatorContext):
        from Hql.Operators.Map import Map
        names = [self.visit(x) for x in ctx.Names]
        return Map(names)

    def visitRenameToExpression(self, ctx: HqlParser.RenameToExpressionContext):
        from Hql.Expressions import ToClause
        src = self.visit(ctx.Source)
        dst = self.visit(ctx.Destination)
        return ToClause(src, dst)
    
    def visitWhereOperator(self, ctx: HqlParser.WhereOperatorContext):
        from Hql.Operators.Where import Where

        predicate = self.visit(ctx.Predicate)
                
        params = []
        for i in ctx.Parameters:
            params.append(self.visit(i))

        if not predicate:
            raise hqle.ParseException('Where instanciated with None type predicate', ctx)
            
        return Where(predicate, params)

    def visitTakeOperator(self, ctx: HqlParser.TakeOperatorContext):
        from Hql.Operators.Take import Take

        limit = self.visit(ctx.Limit)
        
        tables = []
        for i in ctx.Tables:
            tables.append(self.visit(i))
        
        return Take(limit, tables)

    def visitCountOperator(self, ctx: HqlParser.CountOperatorContext):
        from Hql.Operators.Count import Count

        name = self.visit(ctx.Name) if ctx.Name else None
        
        return Count(name)
    
    def visitProjectOperator(self, ctx: HqlParser.ProjectOperatorContext):
        from Hql.Operators.Project import Project

        exprs = []
        for i in ctx.Expressions:
            exprs.append(self.visit(i))
        
        return Project(exprs)

    def visitProjectAwayOperator(self, ctx: HqlParser.ProjectAwayOperatorContext):
        from Hql.Operators.Project import ProjectAway

        exprs = []
        for i in ctx.Columns:
            exprs.append(self.visit(i))
        
        return ProjectAway(exprs)
    
    def visitProjectKeepOperator(self, ctx: HqlParser.ProjectKeepOperatorContext):
        from Hql.Operators.Project import ProjectKeep

        exprs = []
        for i in ctx.Columns:
            exprs.append(self.visit(i))
        
        return ProjectKeep(exprs)

    def visitProjectRenameOperator(self, ctx: HqlParser.ProjectRenameOperatorContext):
        from Hql.Operators.Project import ProjectRename

        exprs = []
        for i in ctx.Expressions:
            exprs.append(self.visit(i))
        
        return ProjectRename(exprs)
    
    def visitProjectReorderOperator(self, ctx: HqlParser.ProjectReorderOperatorContext):
        from Hql.Operators.Project import ProjectReorder

        exprs = []
        for i in ctx.Expressions:
            exprs.append(self.visit(i))
        
        return ProjectReorder(exprs)
        
    def visitExtendOperator(self, ctx: HqlParser.ExtendOperatorContext):
        from Hql.Operators.Extend import Extend

        exprs = []
        for i in ctx.Expressions:
            exprs.append(self.visit(i))
            
        return Extend(exprs)

    def visitRangeExpression(self, ctx: HqlParser.RangeExpressionContext):
        from Hql.Operators.Range import Range

        rangeexpr = Range(
            self.visit(ctx.Expression),
            self.visit(ctx.FromExpression),
            self.visit(ctx.ToExpression),
            self.visit(ctx.StepExpression)
        )
        
        return rangeexpr

    def visitTopOperator(self, ctx: HqlParser.TopOperatorContext):
        from Hql.Operators.Top import Top

        expr = Top(
            self.visit(ctx.Expression),
            self.visit(ctx.ByExpression)
        )
        
        return expr

    def visitUnnestOperator(self, ctx: HqlParser.UnnestOperatorContext):
        from Hql.Operators.Unnest import Unnest
        from Hql.Expressions.References import Wildcard

        field = self.visit(ctx.Field)
        tables = self.visit(ctx.OnClause) if ctx.OnClause else [Wildcard('*')]
        
        return Unnest(field, tables)
    
    def visitUnnestOperatorOnClause(self, ctx: HqlParser.UnnestOperatorOnClauseContext):
        return [self.visit(x) for x in ctx.Expressions]

    def visitUnionOperator(self, ctx: HqlParser.UnionOperatorContext):
        from Hql.Operators.Union import Union

        exprs = [self.visit(x) for x in ctx.Expressions]
        name = self.visit(ctx.TableName) if ctx.TableName else None

        return Union(exprs, name=name)

    def visitSummarizeOperator(self, ctx: HqlParser.SummarizeOperatorContext):
        from Hql.Operators.Summarize import Summarize
        from Hql.Expressions.Aggregation import ByExpression

        by = None
        exprs = []
        for i in ctx.Expressions:
            exprs.append(self.visit(i))
                
        if ctx.ByClause:
            by = self.visit(ctx.ByClause)
            assert isinstance(by, ByExpression)
        
        return Summarize(exprs, by)
    
    def visitSummarizeOperatorByClause(self, ctx: HqlParser.SummarizeOperatorByClauseContext):
        from Hql.Expressions.Aggregation import ByExpression

        exprs = []
        for i in ctx.Expressions:
            exprs.append(self.visit(i))
        
        return ByExpression(exprs)

    def visitDataTableExpression(self, ctx: HqlParser.DataTableExpressionContext):
        from Hql.Operators.Datatable import Datatable

        schema = self.visit(ctx.Schema)
        values = []
        for i in ctx.Values:
            values.append(self.visit(i))

        name = None
        if ctx.TableName:
            name = self.visit(ctx.TableName)
        
        return Datatable(schema, values, name=name)
    
    def visitRowSchema(self, ctx: HqlParser.RowSchemaContext):
        schema = []
        for i in ctx.Columns:
            schema.append(self.visit(i))
        
        return schema
    
    def visitRowSchemaColumnDeclaration(self, ctx: HqlParser.RowSchemaColumnDeclarationContext):
        name = self.visit(ctx.Name)
        t = self.visit(ctx.Type)
        
        return [name, t]

    def visitJoinOperator(self, ctx: HqlParser.JoinOperatorContext):
        from Hql.Operators.Join import Join
        from Hql.Expressions import Expression

        table = self.visit(ctx.Table)
        where = None
        
        params = []
        for i in ctx.Parameters:
            params.append(self.visit(i))
        
        on = self.visit(ctx.OnClause)
        if isinstance(on, Expression):
            on = [on]
        assert isinstance(on, list)
        
        if ctx.WhereClause:
            where = self.visit(ctx.WhereClause)
        
        return Join(table, on, params=params, where=where)
    
    def visitJoinOperatorOnClause(self, ctx: HqlParser.JoinOperatorOnClauseContext):
        exprs = []
        for i in ctx.Expressions:
            exprs.append(self.visit(i))
            
        return exprs
            
    def visitJoinOperatorWhereClause(self, ctx: HqlParser.JoinOperatorWhereClauseContext):
        return self.visit(ctx.Predicate)

    def visitMvexpandOperator(self, ctx: HqlParser.MvexpandOperatorContext):
        from Hql.Operators.MvExpand import MvExpand

        exprs = []
        for i in ctx.Expressions:
            exprs.append(self.visit(i))
        
        if ctx.LimitClause:
            limit = self.visit(ctx.LimitClause)
        else:
            limit = None
        
        return MvExpand(exprs, limit=limit)
    
    def visitMvexpandOperatorExpression(self, ctx: HqlParser.MvexpandOperatorExpressionContext):
        from Hql.Types.Hql import HqlTypes as hqlt
        from Hql.Expressions import ToClause

        expr = self.visit(ctx.Expression)
        
        if ctx.ToClause:
            to:hqlt.HqlType = self.visit(ctx.ToClause)
            return ToClause(expr, to)

        return ToClause(expr)
    
    def visitMvapplyOperatorExpressionToClause(self, ctx: HqlParser.MvapplyOperatorExpressionToClauseContext):
        return self.visit(ctx.Type)

    def visitMvapplyOperatorLimitClause(self, ctx: HqlParser.MvapplyOperatorLimitClauseContext):
        return self.visit(ctx.LimitValue)
    
    def visitSortOperator(self, ctx: HqlParser.SortOperatorContext):
        from Hql.Operators.Sort import Sort

        exprs = []
        for i in ctx.Expressions:
            exprs.append(self.visit(i))
        
        return Sort(exprs)
