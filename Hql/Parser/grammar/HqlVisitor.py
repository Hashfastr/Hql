# Generated from ./Hql.g4 by ANTLR 4.13.2
from antlr4 import *
if "." in __name__:
    from .HqlParser import HqlParser
else:
    from HqlParser import HqlParser

# This class defines a complete generic visitor for a parse tree produced by HqlParser.

class HqlVisitor(ParseTreeVisitor):

    # Visit a parse tree produced by HqlParser#top.
    def visitTop(self, ctx:HqlParser.TopContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#query.
    def visitQuery(self, ctx:HqlParser.QueryContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#statement.
    def visitStatement(self, ctx:HqlParser.StatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#letStatement.
    def visitLetStatement(self, ctx:HqlParser.LetStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#letVariableDeclaration.
    def visitLetVariableDeclaration(self, ctx:HqlParser.LetVariableDeclarationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#letFunctionDeclaration.
    def visitLetFunctionDeclaration(self, ctx:HqlParser.LetFunctionDeclarationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#letViewDeclaration.
    def visitLetViewDeclaration(self, ctx:HqlParser.LetViewDeclarationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#letViewParameterList.
    def visitLetViewParameterList(self, ctx:HqlParser.LetViewParameterListContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#letMaterializeDeclaration.
    def visitLetMaterializeDeclaration(self, ctx:HqlParser.LetMaterializeDeclarationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#letEntityGroupDeclaration.
    def visitLetEntityGroupDeclaration(self, ctx:HqlParser.LetEntityGroupDeclarationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#letLogicDeclaration.
    def visitLetLogicDeclaration(self, ctx:HqlParser.LetLogicDeclarationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#letFunctionParameterList.
    def visitLetFunctionParameterList(self, ctx:HqlParser.LetFunctionParameterListContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#macroStatement.
    def visitMacroStatement(self, ctx:HqlParser.MacroStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#classStatement.
    def visitClassStatement(self, ctx:HqlParser.ClassStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#mapStatement.
    def visitMapStatement(self, ctx:HqlParser.MapStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#mapEntry.
    def visitMapEntry(self, ctx:HqlParser.MapEntryContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#singleMapValue.
    def visitSingleMapValue(self, ctx:HqlParser.SingleMapValueContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#multiMapValue.
    def visitMultiMapValue(self, ctx:HqlParser.MultiMapValueContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#importStatement.
    def visitImportStatement(self, ctx:HqlParser.ImportStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#simpleImportStatement.
    def visitSimpleImportStatement(self, ctx:HqlParser.SimpleImportStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#fromImportStatement.
    def visitFromImportStatement(self, ctx:HqlParser.FromImportStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#scalarParameter.
    def visitScalarParameter(self, ctx:HqlParser.ScalarParameterContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#scalarParameterDefault.
    def visitScalarParameterDefault(self, ctx:HqlParser.ScalarParameterDefaultContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#tabularParameter.
    def visitTabularParameter(self, ctx:HqlParser.TabularParameterContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#tabularParameterOpenSchema.
    def visitTabularParameterOpenSchema(self, ctx:HqlParser.TabularParameterOpenSchemaContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#tabularParameterRowSchema.
    def visitTabularParameterRowSchema(self, ctx:HqlParser.TabularParameterRowSchemaContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#tabularParameterRowSchemaColumnDeclaration.
    def visitTabularParameterRowSchemaColumnDeclaration(self, ctx:HqlParser.TabularParameterRowSchemaColumnDeclarationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#letFunctionBody.
    def visitLetFunctionBody(self, ctx:HqlParser.LetFunctionBodyContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#letFunctionBodyStatement.
    def visitLetFunctionBodyStatement(self, ctx:HqlParser.LetFunctionBodyStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#declarePatternStatement.
    def visitDeclarePatternStatement(self, ctx:HqlParser.DeclarePatternStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#declarePatternDefinition.
    def visitDeclarePatternDefinition(self, ctx:HqlParser.DeclarePatternDefinitionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#declarePatternParameterList.
    def visitDeclarePatternParameterList(self, ctx:HqlParser.DeclarePatternParameterListContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#declarePatternParameter.
    def visitDeclarePatternParameter(self, ctx:HqlParser.DeclarePatternParameterContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#declarePatternPathParameter.
    def visitDeclarePatternPathParameter(self, ctx:HqlParser.DeclarePatternPathParameterContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#declarePatternRule.
    def visitDeclarePatternRule(self, ctx:HqlParser.DeclarePatternRuleContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#declarePatternRuleArgumentList.
    def visitDeclarePatternRuleArgumentList(self, ctx:HqlParser.DeclarePatternRuleArgumentListContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#declarePatternRulePathArgument.
    def visitDeclarePatternRulePathArgument(self, ctx:HqlParser.DeclarePatternRulePathArgumentContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#declarePatternRuleArgument.
    def visitDeclarePatternRuleArgument(self, ctx:HqlParser.DeclarePatternRuleArgumentContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#declarePatternBody.
    def visitDeclarePatternBody(self, ctx:HqlParser.DeclarePatternBodyContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#restrictAccessStatement.
    def visitRestrictAccessStatement(self, ctx:HqlParser.RestrictAccessStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#restrictAccessStatementEntity.
    def visitRestrictAccessStatementEntity(self, ctx:HqlParser.RestrictAccessStatementEntityContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#setStatement.
    def visitSetStatement(self, ctx:HqlParser.SetStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#setStatementOptionValue.
    def visitSetStatementOptionValue(self, ctx:HqlParser.SetStatementOptionValueContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#declareQueryParametersStatement.
    def visitDeclareQueryParametersStatement(self, ctx:HqlParser.DeclareQueryParametersStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#declareQueryParametersStatementParameter.
    def visitDeclareQueryParametersStatementParameter(self, ctx:HqlParser.DeclareQueryParametersStatementParameterContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#queryStatement.
    def visitQueryStatement(self, ctx:HqlParser.QueryStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#expression.
    def visitExpression(self, ctx:HqlParser.ExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#pipeExpression.
    def visitPipeExpression(self, ctx:HqlParser.PipeExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#emptyPipedExpression.
    def visitEmptyPipedExpression(self, ctx:HqlParser.EmptyPipedExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#pipedOperator.
    def visitPipedOperator(self, ctx:HqlParser.PipedOperatorContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#pipeSubExpression.
    def visitPipeSubExpression(self, ctx:HqlParser.PipeSubExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#beforePipeExpression.
    def visitBeforePipeExpression(self, ctx:HqlParser.BeforePipeExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#afterPipeOperator.
    def visitAfterPipeOperator(self, ctx:HqlParser.AfterPipeOperatorContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#beforeOrAfterPipeOperator.
    def visitBeforeOrAfterPipeOperator(self, ctx:HqlParser.BeforeOrAfterPipeOperatorContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#forkPipeOperator.
    def visitForkPipeOperator(self, ctx:HqlParser.ForkPipeOperatorContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#asOperator.
    def visitAsOperator(self, ctx:HqlParser.AsOperatorContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#assertSchemaOperator.
    def visitAssertSchemaOperator(self, ctx:HqlParser.AssertSchemaOperatorContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#consumeOperator.
    def visitConsumeOperator(self, ctx:HqlParser.ConsumeOperatorContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#countOperator.
    def visitCountOperator(self, ctx:HqlParser.CountOperatorContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#distinctOperator.
    def visitDistinctOperator(self, ctx:HqlParser.DistinctOperatorContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#distinctOperatorStarTarget.
    def visitDistinctOperatorStarTarget(self, ctx:HqlParser.DistinctOperatorStarTargetContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#distinctOperatorColumnListTarget.
    def visitDistinctOperatorColumnListTarget(self, ctx:HqlParser.DistinctOperatorColumnListTargetContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#evaluateOperator.
    def visitEvaluateOperator(self, ctx:HqlParser.EvaluateOperatorContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#evaluateOperatorSchemaClause.
    def visitEvaluateOperatorSchemaClause(self, ctx:HqlParser.EvaluateOperatorSchemaClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#extendOperator.
    def visitExtendOperator(self, ctx:HqlParser.ExtendOperatorContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#executeAndCacheOperator.
    def visitExecuteAndCacheOperator(self, ctx:HqlParser.ExecuteAndCacheOperatorContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#facetByOperator.
    def visitFacetByOperator(self, ctx:HqlParser.FacetByOperatorContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#facetByOperatorWithOperatorClause.
    def visitFacetByOperatorWithOperatorClause(self, ctx:HqlParser.FacetByOperatorWithOperatorClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#facetByOperatorWithExpressionClause.
    def visitFacetByOperatorWithExpressionClause(self, ctx:HqlParser.FacetByOperatorWithExpressionClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#findOperator.
    def visitFindOperator(self, ctx:HqlParser.FindOperatorContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#findOperatorParametersWhereClause.
    def visitFindOperatorParametersWhereClause(self, ctx:HqlParser.FindOperatorParametersWhereClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#findOperatorInClause.
    def visitFindOperatorInClause(self, ctx:HqlParser.FindOperatorInClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#findOperatorProjectClause.
    def visitFindOperatorProjectClause(self, ctx:HqlParser.FindOperatorProjectClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#findOperatorProjectExpression.
    def visitFindOperatorProjectExpression(self, ctx:HqlParser.FindOperatorProjectExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#findOperatorColumnExpression.
    def visitFindOperatorColumnExpression(self, ctx:HqlParser.FindOperatorColumnExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#findOperatorOptionalColumnType.
    def visitFindOperatorOptionalColumnType(self, ctx:HqlParser.FindOperatorOptionalColumnTypeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#findOperatorPackExpression.
    def visitFindOperatorPackExpression(self, ctx:HqlParser.FindOperatorPackExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#findOperatorProjectSmartClause.
    def visitFindOperatorProjectSmartClause(self, ctx:HqlParser.FindOperatorProjectSmartClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#findOperatorProjectAwayClause.
    def visitFindOperatorProjectAwayClause(self, ctx:HqlParser.FindOperatorProjectAwayClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#findOperatorProjectAwayStar.
    def visitFindOperatorProjectAwayStar(self, ctx:HqlParser.FindOperatorProjectAwayStarContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#findOperatorProjectAwayColumnList.
    def visitFindOperatorProjectAwayColumnList(self, ctx:HqlParser.FindOperatorProjectAwayColumnListContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#findOperatorSource.
    def visitFindOperatorSource(self, ctx:HqlParser.FindOperatorSourceContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#findOperatorSourceEntityExpression.
    def visitFindOperatorSourceEntityExpression(self, ctx:HqlParser.FindOperatorSourceEntityExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#forkOperator.
    def visitForkOperator(self, ctx:HqlParser.ForkOperatorContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#forkOperatorFork.
    def visitForkOperatorFork(self, ctx:HqlParser.ForkOperatorForkContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#forkOperatorExpressionName.
    def visitForkOperatorExpressionName(self, ctx:HqlParser.ForkOperatorExpressionNameContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#forkOperatorExpression.
    def visitForkOperatorExpression(self, ctx:HqlParser.ForkOperatorExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#forkOperatorPipedOperator.
    def visitForkOperatorPipedOperator(self, ctx:HqlParser.ForkOperatorPipedOperatorContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#getSchemaOperator.
    def visitGetSchemaOperator(self, ctx:HqlParser.GetSchemaOperatorContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#graphMarkComponentsOperator.
    def visitGraphMarkComponentsOperator(self, ctx:HqlParser.GraphMarkComponentsOperatorContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#graphMatchOperator.
    def visitGraphMatchOperator(self, ctx:HqlParser.GraphMatchOperatorContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#graphMatchPattern.
    def visitGraphMatchPattern(self, ctx:HqlParser.GraphMatchPatternContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#graphMatchPatternNode.
    def visitGraphMatchPatternNode(self, ctx:HqlParser.GraphMatchPatternNodeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#graphMatchPatternUnnamedEdge.
    def visitGraphMatchPatternUnnamedEdge(self, ctx:HqlParser.GraphMatchPatternUnnamedEdgeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#graphMatchPatternNamedEdge.
    def visitGraphMatchPatternNamedEdge(self, ctx:HqlParser.GraphMatchPatternNamedEdgeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#graphMatchPatternRange.
    def visitGraphMatchPatternRange(self, ctx:HqlParser.GraphMatchPatternRangeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#graphMatchWhereClause.
    def visitGraphMatchWhereClause(self, ctx:HqlParser.GraphMatchWhereClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#graphMatchProjectClause.
    def visitGraphMatchProjectClause(self, ctx:HqlParser.GraphMatchProjectClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#graphMergeOperator.
    def visitGraphMergeOperator(self, ctx:HqlParser.GraphMergeOperatorContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#graphToTableOperator.
    def visitGraphToTableOperator(self, ctx:HqlParser.GraphToTableOperatorContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#graphToTableOutput.
    def visitGraphToTableOutput(self, ctx:HqlParser.GraphToTableOutputContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#graphToTableAsClause.
    def visitGraphToTableAsClause(self, ctx:HqlParser.GraphToTableAsClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#graphShortestPathsOperator.
    def visitGraphShortestPathsOperator(self, ctx:HqlParser.GraphShortestPathsOperatorContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#invokeOperator.
    def visitInvokeOperator(self, ctx:HqlParser.InvokeOperatorContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#joinOperator.
    def visitJoinOperator(self, ctx:HqlParser.JoinOperatorContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#joinOperatorTable.
    def visitJoinOperatorTable(self, ctx:HqlParser.JoinOperatorTableContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#joinOperatorOnClause.
    def visitJoinOperatorOnClause(self, ctx:HqlParser.JoinOperatorOnClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#joinOperatorWhereClause.
    def visitJoinOperatorWhereClause(self, ctx:HqlParser.JoinOperatorWhereClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#lookupOperator.
    def visitLookupOperator(self, ctx:HqlParser.LookupOperatorContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#macroExpandOperator.
    def visitMacroExpandOperator(self, ctx:HqlParser.MacroExpandOperatorContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#macroExpandEntityGroup.
    def visitMacroExpandEntityGroup(self, ctx:HqlParser.MacroExpandEntityGroupContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#entityGroupExpression.
    def visitEntityGroupExpression(self, ctx:HqlParser.EntityGroupExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#makeGraphOperator.
    def visitMakeGraphOperator(self, ctx:HqlParser.MakeGraphOperatorContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#makeGraphIdClause.
    def visitMakeGraphIdClause(self, ctx:HqlParser.MakeGraphIdClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#makeGraphTablesAndKeysClause.
    def visitMakeGraphTablesAndKeysClause(self, ctx:HqlParser.MakeGraphTablesAndKeysClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#makeGraphPartitionedByClause.
    def visitMakeGraphPartitionedByClause(self, ctx:HqlParser.MakeGraphPartitionedByClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#makeSeriesOperator.
    def visitMakeSeriesOperator(self, ctx:HqlParser.MakeSeriesOperatorContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#makeSeriesOperatorOnClause.
    def visitMakeSeriesOperatorOnClause(self, ctx:HqlParser.MakeSeriesOperatorOnClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#makeSeriesOperatorAggregation.
    def visitMakeSeriesOperatorAggregation(self, ctx:HqlParser.MakeSeriesOperatorAggregationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#makeSeriesOperatorExpressionDefaultClause.
    def visitMakeSeriesOperatorExpressionDefaultClause(self, ctx:HqlParser.MakeSeriesOperatorExpressionDefaultClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#makeSeriesOperatorInRangeClause.
    def visitMakeSeriesOperatorInRangeClause(self, ctx:HqlParser.MakeSeriesOperatorInRangeClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#makeSeriesOperatorFromToStepClause.
    def visitMakeSeriesOperatorFromToStepClause(self, ctx:HqlParser.MakeSeriesOperatorFromToStepClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#makeSeriesOperatorByClause.
    def visitMakeSeriesOperatorByClause(self, ctx:HqlParser.MakeSeriesOperatorByClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#mvapplyOperator.
    def visitMvapplyOperator(self, ctx:HqlParser.MvapplyOperatorContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#mvapplyOperatorLimitClause.
    def visitMvapplyOperatorLimitClause(self, ctx:HqlParser.MvapplyOperatorLimitClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#mvapplyOperatorIdClause.
    def visitMvapplyOperatorIdClause(self, ctx:HqlParser.MvapplyOperatorIdClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#mvapplyOperatorExpression.
    def visitMvapplyOperatorExpression(self, ctx:HqlParser.MvapplyOperatorExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#mvapplyOperatorExpressionToClause.
    def visitMvapplyOperatorExpressionToClause(self, ctx:HqlParser.MvapplyOperatorExpressionToClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#mvexpandOperator.
    def visitMvexpandOperator(self, ctx:HqlParser.MvexpandOperatorContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#mvexpandOperatorExpression.
    def visitMvexpandOperatorExpression(self, ctx:HqlParser.MvexpandOperatorExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#parseOperator.
    def visitParseOperator(self, ctx:HqlParser.ParseOperatorContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#parseOperatorKindClause.
    def visitParseOperatorKindClause(self, ctx:HqlParser.ParseOperatorKindClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#parseOperatorFlagsClause.
    def visitParseOperatorFlagsClause(self, ctx:HqlParser.ParseOperatorFlagsClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#parseOperatorNameAndOptionalType.
    def visitParseOperatorNameAndOptionalType(self, ctx:HqlParser.ParseOperatorNameAndOptionalTypeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#parseOperatorPattern.
    def visitParseOperatorPattern(self, ctx:HqlParser.ParseOperatorPatternContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#parseOperatorPatternSegment.
    def visitParseOperatorPatternSegment(self, ctx:HqlParser.ParseOperatorPatternSegmentContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#parseWhereOperator.
    def visitParseWhereOperator(self, ctx:HqlParser.ParseWhereOperatorContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#parseKvOperator.
    def visitParseKvOperator(self, ctx:HqlParser.ParseKvOperatorContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#parseKvWithClause.
    def visitParseKvWithClause(self, ctx:HqlParser.ParseKvWithClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#partitionOperator.
    def visitPartitionOperator(self, ctx:HqlParser.PartitionOperatorContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#partitionOperatorInClause.
    def visitPartitionOperatorInClause(self, ctx:HqlParser.PartitionOperatorInClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#partitionOperatorSubExpressionBody.
    def visitPartitionOperatorSubExpressionBody(self, ctx:HqlParser.PartitionOperatorSubExpressionBodyContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#partitionOperatorFullExpressionBody.
    def visitPartitionOperatorFullExpressionBody(self, ctx:HqlParser.PartitionOperatorFullExpressionBodyContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#partitionByOperator.
    def visitPartitionByOperator(self, ctx:HqlParser.PartitionByOperatorContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#partitionByOperatorIdClause.
    def visitPartitionByOperatorIdClause(self, ctx:HqlParser.PartitionByOperatorIdClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#printOperator.
    def visitPrintOperator(self, ctx:HqlParser.PrintOperatorContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#projectAwayOperator.
    def visitProjectAwayOperator(self, ctx:HqlParser.ProjectAwayOperatorContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#projectKeepOperator.
    def visitProjectKeepOperator(self, ctx:HqlParser.ProjectKeepOperatorContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#projectOperator.
    def visitProjectOperator(self, ctx:HqlParser.ProjectOperatorContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#projectRenameOperator.
    def visitProjectRenameOperator(self, ctx:HqlParser.ProjectRenameOperatorContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#projectReorderOperator.
    def visitProjectReorderOperator(self, ctx:HqlParser.ProjectReorderOperatorContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#projectReorderExpression.
    def visitProjectReorderExpression(self, ctx:HqlParser.ProjectReorderExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#pushOperator.
    def visitPushOperator(self, ctx:HqlParser.PushOperatorContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#reduceByOperator.
    def visitReduceByOperator(self, ctx:HqlParser.ReduceByOperatorContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#reduceByWithClause.
    def visitReduceByWithClause(self, ctx:HqlParser.ReduceByWithClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#renameOperator.
    def visitRenameOperator(self, ctx:HqlParser.RenameOperatorContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#renameToExpression.
    def visitRenameToExpression(self, ctx:HqlParser.RenameToExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#renderOperator.
    def visitRenderOperator(self, ctx:HqlParser.RenderOperatorContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#renderOperatorWithClause.
    def visitRenderOperatorWithClause(self, ctx:HqlParser.RenderOperatorWithClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#renderOperatorLegacyPropertyList.
    def visitRenderOperatorLegacyPropertyList(self, ctx:HqlParser.RenderOperatorLegacyPropertyListContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#renderOperatorProperty.
    def visitRenderOperatorProperty(self, ctx:HqlParser.RenderOperatorPropertyContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#renderPropertyNameList.
    def visitRenderPropertyNameList(self, ctx:HqlParser.RenderPropertyNameListContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#renderOperatorLegacyProperty.
    def visitRenderOperatorLegacyProperty(self, ctx:HqlParser.RenderOperatorLegacyPropertyContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#sampleDistinctOperator.
    def visitSampleDistinctOperator(self, ctx:HqlParser.SampleDistinctOperatorContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#sampleOperator.
    def visitSampleOperator(self, ctx:HqlParser.SampleOperatorContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#scanOperator.
    def visitScanOperator(self, ctx:HqlParser.ScanOperatorContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#scanOperatorOrderByClause.
    def visitScanOperatorOrderByClause(self, ctx:HqlParser.ScanOperatorOrderByClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#scanOperatorPartitionByClause.
    def visitScanOperatorPartitionByClause(self, ctx:HqlParser.ScanOperatorPartitionByClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#scanOperatorDeclareClause.
    def visitScanOperatorDeclareClause(self, ctx:HqlParser.ScanOperatorDeclareClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#scanOperatorStep.
    def visitScanOperatorStep(self, ctx:HqlParser.ScanOperatorStepContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#scanOperatorStepOutputClause.
    def visitScanOperatorStepOutputClause(self, ctx:HqlParser.ScanOperatorStepOutputClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#scanOperatorBody.
    def visitScanOperatorBody(self, ctx:HqlParser.ScanOperatorBodyContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#scanOperatorAssignment.
    def visitScanOperatorAssignment(self, ctx:HqlParser.ScanOperatorAssignmentContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#searchOperator.
    def visitSearchOperator(self, ctx:HqlParser.SearchOperatorContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#searchOperatorStarAndExpression.
    def visitSearchOperatorStarAndExpression(self, ctx:HqlParser.SearchOperatorStarAndExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#searchOperatorInClause.
    def visitSearchOperatorInClause(self, ctx:HqlParser.SearchOperatorInClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#serializeOperator.
    def visitSerializeOperator(self, ctx:HqlParser.SerializeOperatorContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#sortOperator.
    def visitSortOperator(self, ctx:HqlParser.SortOperatorContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#orderedExpression.
    def visitOrderedExpression(self, ctx:HqlParser.OrderedExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#summarizeOperator.
    def visitSummarizeOperator(self, ctx:HqlParser.SummarizeOperatorContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#summarizeOperatorByClause.
    def visitSummarizeOperatorByClause(self, ctx:HqlParser.SummarizeOperatorByClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#summarizeOperatorLegacyBinClause.
    def visitSummarizeOperatorLegacyBinClause(self, ctx:HqlParser.SummarizeOperatorLegacyBinClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#takeOperator.
    def visitTakeOperator(self, ctx:HqlParser.TakeOperatorContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#topOperator.
    def visitTopOperator(self, ctx:HqlParser.TopOperatorContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#topHittersOperator.
    def visitTopHittersOperator(self, ctx:HqlParser.TopHittersOperatorContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#topHittersOperatorByClause.
    def visitTopHittersOperatorByClause(self, ctx:HqlParser.TopHittersOperatorByClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#topNestedOperator.
    def visitTopNestedOperator(self, ctx:HqlParser.TopNestedOperatorContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#topNestedOperatorPart.
    def visitTopNestedOperatorPart(self, ctx:HqlParser.TopNestedOperatorPartContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#topNestedOperatorWithOthersClause.
    def visitTopNestedOperatorWithOthersClause(self, ctx:HqlParser.TopNestedOperatorWithOthersClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#unionOperator.
    def visitUnionOperator(self, ctx:HqlParser.UnionOperatorContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#unionAsOperator.
    def visitUnionAsOperator(self, ctx:HqlParser.UnionAsOperatorContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#whereOperator.
    def visitWhereOperator(self, ctx:HqlParser.WhereOperatorContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#unnestOperator.
    def visitUnnestOperator(self, ctx:HqlParser.UnnestOperatorContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#unnestOperatorOnClause.
    def visitUnnestOperatorOnClause(self, ctx:HqlParser.UnnestOperatorOnClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#contextualSubExpression.
    def visitContextualSubExpression(self, ctx:HqlParser.ContextualSubExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#contextualPipeExpression.
    def visitContextualPipeExpression(self, ctx:HqlParser.ContextualPipeExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#contextualPipeExpressionPipedOperator.
    def visitContextualPipeExpressionPipedOperator(self, ctx:HqlParser.ContextualPipeExpressionPipedOperatorContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#strictQueryOperatorParameter.
    def visitStrictQueryOperatorParameter(self, ctx:HqlParser.StrictQueryOperatorParameterContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#relaxedQueryOperatorParameter.
    def visitRelaxedQueryOperatorParameter(self, ctx:HqlParser.RelaxedQueryOperatorParameterContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#queryOperatorProperty.
    def visitQueryOperatorProperty(self, ctx:HqlParser.QueryOperatorPropertyContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#namedExpression.
    def visitNamedExpression(self, ctx:HqlParser.NamedExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#staticNamedExpression.
    def visitStaticNamedExpression(self, ctx:HqlParser.StaticNamedExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#namedExpressionNameClause.
    def visitNamedExpressionNameClause(self, ctx:HqlParser.NamedExpressionNameClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#namedExpressionNameList.
    def visitNamedExpressionNameList(self, ctx:HqlParser.NamedExpressionNameListContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#scopedFunctionCallExpression.
    def visitScopedFunctionCallExpression(self, ctx:HqlParser.ScopedFunctionCallExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#unnamedExpression.
    def visitUnnamedExpression(self, ctx:HqlParser.UnnamedExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#logicalOrExpression.
    def visitLogicalOrExpression(self, ctx:HqlParser.LogicalOrExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#logicalOrOperation.
    def visitLogicalOrOperation(self, ctx:HqlParser.LogicalOrOperationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#logicalAndExpression.
    def visitLogicalAndExpression(self, ctx:HqlParser.LogicalAndExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#logicalAndOperation.
    def visitLogicalAndOperation(self, ctx:HqlParser.LogicalAndOperationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#equalityExpression.
    def visitEqualityExpression(self, ctx:HqlParser.EqualityExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#equalsEqualityExpression.
    def visitEqualsEqualityExpression(self, ctx:HqlParser.EqualsEqualityExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#listEqualityExpression.
    def visitListEqualityExpression(self, ctx:HqlParser.ListEqualityExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#betweenEqualityExpression.
    def visitBetweenEqualityExpression(self, ctx:HqlParser.BetweenEqualityExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#starEqualityExpression.
    def visitStarEqualityExpression(self, ctx:HqlParser.StarEqualityExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#relationalExpression.
    def visitRelationalExpression(self, ctx:HqlParser.RelationalExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#additiveExpression.
    def visitAdditiveExpression(self, ctx:HqlParser.AdditiveExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#additiveOperation.
    def visitAdditiveOperation(self, ctx:HqlParser.AdditiveOperationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#multiplicativeExpression.
    def visitMultiplicativeExpression(self, ctx:HqlParser.MultiplicativeExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#multiplicativeOperation.
    def visitMultiplicativeOperation(self, ctx:HqlParser.MultiplicativeOperationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#stringOperatorExpression.
    def visitStringOperatorExpression(self, ctx:HqlParser.StringOperatorExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#stringBinaryOperatorExpression.
    def visitStringBinaryOperatorExpression(self, ctx:HqlParser.StringBinaryOperatorExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#stringBinaryOperator.
    def visitStringBinaryOperator(self, ctx:HqlParser.StringBinaryOperatorContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#stringStarOperatorExpression.
    def visitStringStarOperatorExpression(self, ctx:HqlParser.StringStarOperatorExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#invocationExpression.
    def visitInvocationExpression(self, ctx:HqlParser.InvocationExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#functionCallOrPathExpression.
    def visitFunctionCallOrPathExpression(self, ctx:HqlParser.FunctionCallOrPathExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#functionCallOrPathRoot.
    def visitFunctionCallOrPathRoot(self, ctx:HqlParser.FunctionCallOrPathRootContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#functionCallOrPathPathExpression.
    def visitFunctionCallOrPathPathExpression(self, ctx:HqlParser.FunctionCallOrPathPathExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#functionCallOrPathOperation.
    def visitFunctionCallOrPathOperation(self, ctx:HqlParser.FunctionCallOrPathOperationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#functionCallOrPathCallOperation.
    def visitFunctionCallOrPathCallOperation(self, ctx:HqlParser.FunctionCallOrPathCallOperationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#functionalCallOrPathPathOperation.
    def visitFunctionalCallOrPathPathOperation(self, ctx:HqlParser.FunctionalCallOrPathPathOperationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#functionCallOrPathElementOperation.
    def visitFunctionCallOrPathElementOperation(self, ctx:HqlParser.FunctionCallOrPathElementOperationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#legacyFunctionCallOrPathElementOperation.
    def visitLegacyFunctionCallOrPathElementOperation(self, ctx:HqlParser.LegacyFunctionCallOrPathElementOperationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#toScalarExpression.
    def visitToScalarExpression(self, ctx:HqlParser.ToScalarExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#toTableExpression.
    def visitToTableExpression(self, ctx:HqlParser.ToTableExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#noOptimizationParameter.
    def visitNoOptimizationParameter(self, ctx:HqlParser.NoOptimizationParameterContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#dotCompositeFunctionCallExpression.
    def visitDotCompositeFunctionCallExpression(self, ctx:HqlParser.DotCompositeFunctionCallExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#dotCompositeFunctionCallOperation.
    def visitDotCompositeFunctionCallOperation(self, ctx:HqlParser.DotCompositeFunctionCallOperationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#functionCallExpression.
    def visitFunctionCallExpression(self, ctx:HqlParser.FunctionCallExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#functionCallName.
    def visitFunctionCallName(self, ctx:HqlParser.FunctionCallNameContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#argumentExpression.
    def visitArgumentExpression(self, ctx:HqlParser.ArgumentExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#starExpression.
    def visitStarExpression(self, ctx:HqlParser.StarExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#primaryExpression.
    def visitPrimaryExpression(self, ctx:HqlParser.PrimaryExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#parenthesizedExpression.
    def visitParenthesizedExpression(self, ctx:HqlParser.ParenthesizedExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#rangeExpression.
    def visitRangeExpression(self, ctx:HqlParser.RangeExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#entityExpression.
    def visitEntityExpression(self, ctx:HqlParser.EntityExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#entityPathOrElementExpression.
    def visitEntityPathOrElementExpression(self, ctx:HqlParser.EntityPathOrElementExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#entityPathOrElementOperator.
    def visitEntityPathOrElementOperator(self, ctx:HqlParser.EntityPathOrElementOperatorContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#entityPathOperator.
    def visitEntityPathOperator(self, ctx:HqlParser.EntityPathOperatorContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#entityElementOperator.
    def visitEntityElementOperator(self, ctx:HqlParser.EntityElementOperatorContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#legacyEntityPathElementOperator.
    def visitLegacyEntityPathElementOperator(self, ctx:HqlParser.LegacyEntityPathElementOperatorContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#entityName.
    def visitEntityName(self, ctx:HqlParser.EntityNameContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#entityNameReference.
    def visitEntityNameReference(self, ctx:HqlParser.EntityNameReferenceContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#atSignName.
    def visitAtSignName(self, ctx:HqlParser.AtSignNameContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#extendedPathName.
    def visitExtendedPathName(self, ctx:HqlParser.ExtendedPathNameContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#wildcardedEntityExpression.
    def visitWildcardedEntityExpression(self, ctx:HqlParser.WildcardedEntityExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#wildcardedPathExpression.
    def visitWildcardedPathExpression(self, ctx:HqlParser.WildcardedPathExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#wildcardedPathName.
    def visitWildcardedPathName(self, ctx:HqlParser.WildcardedPathNameContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#contextualDataTableExpression.
    def visitContextualDataTableExpression(self, ctx:HqlParser.ContextualDataTableExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#dataTableExpression.
    def visitDataTableExpression(self, ctx:HqlParser.DataTableExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#rowSchema.
    def visitRowSchema(self, ctx:HqlParser.RowSchemaContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#rowSchemaColumnDeclaration.
    def visitRowSchemaColumnDeclaration(self, ctx:HqlParser.RowSchemaColumnDeclarationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#externalDataExpression.
    def visitExternalDataExpression(self, ctx:HqlParser.ExternalDataExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#externalDataWithClause.
    def visitExternalDataWithClause(self, ctx:HqlParser.ExternalDataWithClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#externalDataWithClauseProperty.
    def visitExternalDataWithClauseProperty(self, ctx:HqlParser.ExternalDataWithClausePropertyContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#materializedViewCombineExpression.
    def visitMaterializedViewCombineExpression(self, ctx:HqlParser.MaterializedViewCombineExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#materializeViewCombineBaseClause.
    def visitMaterializeViewCombineBaseClause(self, ctx:HqlParser.MaterializeViewCombineBaseClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#materializedViewCombineDeltaClause.
    def visitMaterializedViewCombineDeltaClause(self, ctx:HqlParser.MaterializedViewCombineDeltaClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#materializedViewCombineAggregationsClause.
    def visitMaterializedViewCombineAggregationsClause(self, ctx:HqlParser.MaterializedViewCombineAggregationsClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#scalarType.
    def visitScalarType(self, ctx:HqlParser.ScalarTypeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#extendedScalarType.
    def visitExtendedScalarType(self, ctx:HqlParser.ExtendedScalarTypeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#parameterName.
    def visitParameterName(self, ctx:HqlParser.ParameterNameContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#simpleNameReference.
    def visitSimpleNameReference(self, ctx:HqlParser.SimpleNameReferenceContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#extendedNameReference.
    def visitExtendedNameReference(self, ctx:HqlParser.ExtendedNameReferenceContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#wildcardedNameReference.
    def visitWildcardedNameReference(self, ctx:HqlParser.WildcardedNameReferenceContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#simpleOrWildcardedNameReference.
    def visitSimpleOrWildcardedNameReference(self, ctx:HqlParser.SimpleOrWildcardedNameReferenceContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#pathReference.
    def visitPathReference(self, ctx:HqlParser.PathReferenceContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#simpleOrPathNameReference.
    def visitSimpleOrPathNameReference(self, ctx:HqlParser.SimpleOrPathNameReferenceContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#tableNameReference.
    def visitTableNameReference(self, ctx:HqlParser.TableNameReferenceContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#dynamicTableNameReference.
    def visitDynamicTableNameReference(self, ctx:HqlParser.DynamicTableNameReferenceContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#identifierName.
    def visitIdentifierName(self, ctx:HqlParser.IdentifierNameContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#keywordName.
    def visitKeywordName(self, ctx:HqlParser.KeywordNameContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#extendedKeywordName.
    def visitExtendedKeywordName(self, ctx:HqlParser.ExtendedKeywordNameContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#escapedName.
    def visitEscapedName(self, ctx:HqlParser.EscapedNameContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#pathOrKeyword.
    def visitPathOrKeyword(self, ctx:HqlParser.PathOrKeywordContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#pathOrExtendedKeyword.
    def visitPathOrExtendedKeyword(self, ctx:HqlParser.PathOrExtendedKeywordContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#wildcardedName.
    def visitWildcardedName(self, ctx:HqlParser.WildcardedNameContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#literalExpression.
    def visitLiteralExpression(self, ctx:HqlParser.LiteralExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#unsignedLiteralExpression.
    def visitUnsignedLiteralExpression(self, ctx:HqlParser.UnsignedLiteralExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#numberLikeLiteralExpression.
    def visitNumberLikeLiteralExpression(self, ctx:HqlParser.NumberLikeLiteralExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#numericLiteralExpression.
    def visitNumericLiteralExpression(self, ctx:HqlParser.NumericLiteralExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#signedLiteralExpression.
    def visitSignedLiteralExpression(self, ctx:HqlParser.SignedLiteralExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#longLiteralExpression.
    def visitLongLiteralExpression(self, ctx:HqlParser.LongLiteralExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#intLiteralExpression.
    def visitIntLiteralExpression(self, ctx:HqlParser.IntLiteralExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#realLiteralExpression.
    def visitRealLiteralExpression(self, ctx:HqlParser.RealLiteralExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#decimalLiteralExpression.
    def visitDecimalLiteralExpression(self, ctx:HqlParser.DecimalLiteralExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#dateTimeLiteralExpression.
    def visitDateTimeLiteralExpression(self, ctx:HqlParser.DateTimeLiteralExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#timeSpanLiteralExpression.
    def visitTimeSpanLiteralExpression(self, ctx:HqlParser.TimeSpanLiteralExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#booleanLiteralExpression.
    def visitBooleanLiteralExpression(self, ctx:HqlParser.BooleanLiteralExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#guidLiteralExpression.
    def visitGuidLiteralExpression(self, ctx:HqlParser.GuidLiteralExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#typeLiteralExpression.
    def visitTypeLiteralExpression(self, ctx:HqlParser.TypeLiteralExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#signedLongLiteralExpression.
    def visitSignedLongLiteralExpression(self, ctx:HqlParser.SignedLongLiteralExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#signedRealLiteralExpression.
    def visitSignedRealLiteralExpression(self, ctx:HqlParser.SignedRealLiteralExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#stringLiteralExpression.
    def visitStringLiteralExpression(self, ctx:HqlParser.StringLiteralExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#dynamicLiteralExpression.
    def visitDynamicLiteralExpression(self, ctx:HqlParser.DynamicLiteralExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#jsonValue.
    def visitJsonValue(self, ctx:HqlParser.JsonValueContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#jsonObject.
    def visitJsonObject(self, ctx:HqlParser.JsonObjectContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#jsonPair.
    def visitJsonPair(self, ctx:HqlParser.JsonPairContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#jsonArray.
    def visitJsonArray(self, ctx:HqlParser.JsonArrayContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#jsonBoolean.
    def visitJsonBoolean(self, ctx:HqlParser.JsonBooleanContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#jsonDateTime.
    def visitJsonDateTime(self, ctx:HqlParser.JsonDateTimeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#jsonGuid.
    def visitJsonGuid(self, ctx:HqlParser.JsonGuidContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#jsonNull.
    def visitJsonNull(self, ctx:HqlParser.JsonNullContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#jsonString.
    def visitJsonString(self, ctx:HqlParser.JsonStringContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#jsonTimeSpan.
    def visitJsonTimeSpan(self, ctx:HqlParser.JsonTimeSpanContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#jsonLong.
    def visitJsonLong(self, ctx:HqlParser.JsonLongContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by HqlParser#jsonReal.
    def visitJsonReal(self, ctx:HqlParser.JsonRealContext):
        return self.visitChildren(ctx)



del HqlParser