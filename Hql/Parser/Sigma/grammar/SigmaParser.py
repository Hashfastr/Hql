# Generated from Sigma.g4 by ANTLR 4.13.2
# encoding: utf-8
from antlr4 import *
from io import StringIO
import sys
if sys.version_info[1] > 5:
	from typing import TextIO
else:
	from typing.io import TextIO

def serializedATN():
    return [
        4,1,13,79,2,0,7,0,2,1,7,1,2,2,7,2,2,3,7,3,2,4,7,4,2,5,7,5,2,6,7,
        6,2,7,7,7,2,8,7,8,2,9,7,9,2,10,7,10,2,11,7,11,2,12,7,12,1,0,1,0,
        1,0,1,1,1,1,1,1,5,1,33,8,1,10,1,12,1,36,9,1,1,2,1,2,1,2,5,2,41,8,
        2,10,2,12,2,44,9,2,1,3,1,3,1,3,1,3,3,3,50,8,3,1,4,1,4,1,4,1,5,1,
        5,1,5,1,5,1,6,1,6,1,6,1,6,1,7,1,7,3,7,65,8,7,1,8,1,8,3,8,69,8,8,
        1,9,1,9,1,10,1,10,1,11,1,11,1,12,1,12,1,12,0,0,13,0,2,4,6,8,10,12,
        14,16,18,20,22,24,0,0,72,0,26,1,0,0,0,2,29,1,0,0,0,4,37,1,0,0,0,
        6,49,1,0,0,0,8,51,1,0,0,0,10,54,1,0,0,0,12,58,1,0,0,0,14,64,1,0,
        0,0,16,68,1,0,0,0,18,70,1,0,0,0,20,72,1,0,0,0,22,74,1,0,0,0,24,76,
        1,0,0,0,26,27,3,2,1,0,27,28,5,0,0,1,28,1,1,0,0,0,29,34,3,4,2,0,30,
        31,5,2,0,0,31,33,3,4,2,0,32,30,1,0,0,0,33,36,1,0,0,0,34,32,1,0,0,
        0,34,35,1,0,0,0,35,3,1,0,0,0,36,34,1,0,0,0,37,42,3,6,3,0,38,39,5,
        1,0,0,39,41,3,6,3,0,40,38,1,0,0,0,41,44,1,0,0,0,42,40,1,0,0,0,42,
        43,1,0,0,0,43,5,1,0,0,0,44,42,1,0,0,0,45,50,3,12,6,0,46,50,3,8,4,
        0,47,50,3,10,5,0,48,50,3,18,9,0,49,45,1,0,0,0,49,46,1,0,0,0,49,47,
        1,0,0,0,49,48,1,0,0,0,50,7,1,0,0,0,51,52,5,3,0,0,52,53,3,6,3,0,53,
        9,1,0,0,0,54,55,5,7,0,0,55,56,3,2,1,0,56,57,5,8,0,0,57,11,1,0,0,
        0,58,59,3,14,7,0,59,60,5,4,0,0,60,61,3,16,8,0,61,13,1,0,0,0,62,65,
        5,10,0,0,63,65,5,5,0,0,64,62,1,0,0,0,64,63,1,0,0,0,65,15,1,0,0,0,
        66,69,5,6,0,0,67,69,3,20,10,0,68,66,1,0,0,0,68,67,1,0,0,0,69,17,
        1,0,0,0,70,71,3,22,11,0,71,19,1,0,0,0,72,73,3,24,12,0,73,21,1,0,
        0,0,74,75,5,11,0,0,75,23,1,0,0,0,76,77,5,12,0,0,77,25,1,0,0,0,5,
        34,42,49,64,68
    ]

class SigmaParser ( Parser ):

    grammarFileName = "Sigma.g4"

    atn = ATNDeserializer().deserialize(serializedATN())

    decisionsToDFA = [ DFA(ds, i) for i, ds in enumerate(atn.decisionToState) ]

    sharedContextCache = PredictionContextCache()

    literalNames = [ "<INVALID>", "'and'", "'or'", "'not'", "'of'", "'all'", 
                     "'them'", "'('", "')'", "'*'" ]

    symbolicNames = [ "<INVALID>", "AND", "OR", "NOT", "OF", "ALL", "THEM", 
                      "LP", "RP", "ASTERISK", "INT", "IDENTIFIER", "WILDCARD", 
                      "WHITESPACE" ]

    RULE_condition = 0
    RULE_orStatement = 1
    RULE_andStatement = 2
    RULE_statement = 3
    RULE_notStatement = 4
    RULE_bracketStatement = 5
    RULE_ofStatement = 6
    RULE_ofSpecifier = 7
    RULE_ofTarget = 8
    RULE_selectionIdentifier = 9
    RULE_patternIdentifier = 10
    RULE_basicIdentifier = 11
    RULE_wildcardIdentifier = 12

    ruleNames =  [ "condition", "orStatement", "andStatement", "statement", 
                   "notStatement", "bracketStatement", "ofStatement", "ofSpecifier", 
                   "ofTarget", "selectionIdentifier", "patternIdentifier", 
                   "basicIdentifier", "wildcardIdentifier" ]

    EOF = Token.EOF
    AND=1
    OR=2
    NOT=3
    OF=4
    ALL=5
    THEM=6
    LP=7
    RP=8
    ASTERISK=9
    INT=10
    IDENTIFIER=11
    WILDCARD=12
    WHITESPACE=13

    def __init__(self, input:TokenStream, output:TextIO = sys.stdout):
        super().__init__(input, output)
        self.checkVersion("4.13.2")
        self._interp = ParserATNSimulator(self, self.atn, self.decisionsToDFA, self.sharedContextCache)
        self._predicates = None




    class ConditionContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser
            self.Statement = None # OrStatementContext

        def EOF(self):
            return self.getToken(SigmaParser.EOF, 0)

        def orStatement(self):
            return self.getTypedRuleContext(SigmaParser.OrStatementContext,0)


        def getRuleIndex(self):
            return SigmaParser.RULE_condition

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterCondition" ):
                listener.enterCondition(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitCondition" ):
                listener.exitCondition(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitCondition" ):
                return visitor.visitCondition(self)
            else:
                return visitor.visitChildren(self)




    def condition(self):

        localctx = SigmaParser.ConditionContext(self, self._ctx, self.state)
        self.enterRule(localctx, 0, self.RULE_condition)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 26
            localctx.Statement = self.orStatement()
            self.state = 27
            self.match(SigmaParser.EOF)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class OrStatementContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser
            self.Left = None # AndStatementContext
            self._andStatement = None # AndStatementContext
            self.Right = list() # of AndStatementContexts

        def andStatement(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(SigmaParser.AndStatementContext)
            else:
                return self.getTypedRuleContext(SigmaParser.AndStatementContext,i)


        def OR(self, i:int=None):
            if i is None:
                return self.getTokens(SigmaParser.OR)
            else:
                return self.getToken(SigmaParser.OR, i)

        def getRuleIndex(self):
            return SigmaParser.RULE_orStatement

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterOrStatement" ):
                listener.enterOrStatement(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitOrStatement" ):
                listener.exitOrStatement(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitOrStatement" ):
                return visitor.visitOrStatement(self)
            else:
                return visitor.visitChildren(self)




    def orStatement(self):

        localctx = SigmaParser.OrStatementContext(self, self._ctx, self.state)
        self.enterRule(localctx, 2, self.RULE_orStatement)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 29
            localctx.Left = self.andStatement()
            self.state = 34
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==2:
                self.state = 30
                self.match(SigmaParser.OR)
                self.state = 31
                localctx._andStatement = self.andStatement()
                localctx.Right.append(localctx._andStatement)
                self.state = 36
                self._errHandler.sync(self)
                _la = self._input.LA(1)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class AndStatementContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser
            self.Left = None # StatementContext
            self._statement = None # StatementContext
            self.Right = list() # of StatementContexts

        def statement(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(SigmaParser.StatementContext)
            else:
                return self.getTypedRuleContext(SigmaParser.StatementContext,i)


        def AND(self, i:int=None):
            if i is None:
                return self.getTokens(SigmaParser.AND)
            else:
                return self.getToken(SigmaParser.AND, i)

        def getRuleIndex(self):
            return SigmaParser.RULE_andStatement

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterAndStatement" ):
                listener.enterAndStatement(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitAndStatement" ):
                listener.exitAndStatement(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitAndStatement" ):
                return visitor.visitAndStatement(self)
            else:
                return visitor.visitChildren(self)




    def andStatement(self):

        localctx = SigmaParser.AndStatementContext(self, self._ctx, self.state)
        self.enterRule(localctx, 4, self.RULE_andStatement)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 37
            localctx.Left = self.statement()
            self.state = 42
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==1:
                self.state = 38
                self.match(SigmaParser.AND)
                self.state = 39
                localctx._statement = self.statement()
                localctx.Right.append(localctx._statement)
                self.state = 44
                self._errHandler.sync(self)
                _la = self._input.LA(1)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class StatementContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def ofStatement(self):
            return self.getTypedRuleContext(SigmaParser.OfStatementContext,0)


        def notStatement(self):
            return self.getTypedRuleContext(SigmaParser.NotStatementContext,0)


        def bracketStatement(self):
            return self.getTypedRuleContext(SigmaParser.BracketStatementContext,0)


        def selectionIdentifier(self):
            return self.getTypedRuleContext(SigmaParser.SelectionIdentifierContext,0)


        def getRuleIndex(self):
            return SigmaParser.RULE_statement

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterStatement" ):
                listener.enterStatement(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitStatement" ):
                listener.exitStatement(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitStatement" ):
                return visitor.visitStatement(self)
            else:
                return visitor.visitChildren(self)




    def statement(self):

        localctx = SigmaParser.StatementContext(self, self._ctx, self.state)
        self.enterRule(localctx, 6, self.RULE_statement)
        try:
            self.state = 49
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [5, 10]:
                self.enterOuterAlt(localctx, 1)
                self.state = 45
                self.ofStatement()
                pass
            elif token in [3]:
                self.enterOuterAlt(localctx, 2)
                self.state = 46
                self.notStatement()
                pass
            elif token in [7]:
                self.enterOuterAlt(localctx, 3)
                self.state = 47
                self.bracketStatement()
                pass
            elif token in [11]:
                self.enterOuterAlt(localctx, 4)
                self.state = 48
                self.selectionIdentifier()
                pass
            else:
                raise NoViableAltException(self)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class NotStatementContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser
            self.Statement = None # StatementContext

        def NOT(self):
            return self.getToken(SigmaParser.NOT, 0)

        def statement(self):
            return self.getTypedRuleContext(SigmaParser.StatementContext,0)


        def getRuleIndex(self):
            return SigmaParser.RULE_notStatement

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterNotStatement" ):
                listener.enterNotStatement(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitNotStatement" ):
                listener.exitNotStatement(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitNotStatement" ):
                return visitor.visitNotStatement(self)
            else:
                return visitor.visitChildren(self)




    def notStatement(self):

        localctx = SigmaParser.NotStatementContext(self, self._ctx, self.state)
        self.enterRule(localctx, 8, self.RULE_notStatement)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 51
            self.match(SigmaParser.NOT)
            self.state = 52
            localctx.Statement = self.statement()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class BracketStatementContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser
            self.Statement = None # OrStatementContext

        def LP(self):
            return self.getToken(SigmaParser.LP, 0)

        def RP(self):
            return self.getToken(SigmaParser.RP, 0)

        def orStatement(self):
            return self.getTypedRuleContext(SigmaParser.OrStatementContext,0)


        def getRuleIndex(self):
            return SigmaParser.RULE_bracketStatement

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterBracketStatement" ):
                listener.enterBracketStatement(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitBracketStatement" ):
                listener.exitBracketStatement(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitBracketStatement" ):
                return visitor.visitBracketStatement(self)
            else:
                return visitor.visitChildren(self)




    def bracketStatement(self):

        localctx = SigmaParser.BracketStatementContext(self, self._ctx, self.state)
        self.enterRule(localctx, 10, self.RULE_bracketStatement)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 54
            self.match(SigmaParser.LP)
            self.state = 55
            localctx.Statement = self.orStatement()
            self.state = 56
            self.match(SigmaParser.RP)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class OfStatementContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser
            self.Specifier = None # OfSpecifierContext
            self.Target = None # OfTargetContext

        def OF(self):
            return self.getToken(SigmaParser.OF, 0)

        def ofSpecifier(self):
            return self.getTypedRuleContext(SigmaParser.OfSpecifierContext,0)


        def ofTarget(self):
            return self.getTypedRuleContext(SigmaParser.OfTargetContext,0)


        def getRuleIndex(self):
            return SigmaParser.RULE_ofStatement

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterOfStatement" ):
                listener.enterOfStatement(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitOfStatement" ):
                listener.exitOfStatement(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitOfStatement" ):
                return visitor.visitOfStatement(self)
            else:
                return visitor.visitChildren(self)




    def ofStatement(self):

        localctx = SigmaParser.OfStatementContext(self, self._ctx, self.state)
        self.enterRule(localctx, 12, self.RULE_ofStatement)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 58
            localctx.Specifier = self.ofSpecifier()
            self.state = 59
            self.match(SigmaParser.OF)
            self.state = 60
            localctx.Target = self.ofTarget()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class OfSpecifierContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser
            self.Int = None # Token
            self.All = None # Token

        def INT(self):
            return self.getToken(SigmaParser.INT, 0)

        def ALL(self):
            return self.getToken(SigmaParser.ALL, 0)

        def getRuleIndex(self):
            return SigmaParser.RULE_ofSpecifier

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterOfSpecifier" ):
                listener.enterOfSpecifier(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitOfSpecifier" ):
                listener.exitOfSpecifier(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitOfSpecifier" ):
                return visitor.visitOfSpecifier(self)
            else:
                return visitor.visitChildren(self)




    def ofSpecifier(self):

        localctx = SigmaParser.OfSpecifierContext(self, self._ctx, self.state)
        self.enterRule(localctx, 14, self.RULE_ofSpecifier)
        try:
            self.state = 64
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [10]:
                self.enterOuterAlt(localctx, 1)
                self.state = 62
                localctx.Int = self.match(SigmaParser.INT)
                pass
            elif token in [5]:
                self.enterOuterAlt(localctx, 2)
                self.state = 63
                localctx.All = self.match(SigmaParser.ALL)
                pass
            else:
                raise NoViableAltException(self)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class OfTargetContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser
            self.Them = None # Token
            self.Pattern = None # PatternIdentifierContext

        def THEM(self):
            return self.getToken(SigmaParser.THEM, 0)

        def patternIdentifier(self):
            return self.getTypedRuleContext(SigmaParser.PatternIdentifierContext,0)


        def getRuleIndex(self):
            return SigmaParser.RULE_ofTarget

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterOfTarget" ):
                listener.enterOfTarget(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitOfTarget" ):
                listener.exitOfTarget(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitOfTarget" ):
                return visitor.visitOfTarget(self)
            else:
                return visitor.visitChildren(self)




    def ofTarget(self):

        localctx = SigmaParser.OfTargetContext(self, self._ctx, self.state)
        self.enterRule(localctx, 16, self.RULE_ofTarget)
        try:
            self.state = 68
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [6]:
                self.enterOuterAlt(localctx, 1)
                self.state = 66
                localctx.Them = self.match(SigmaParser.THEM)
                pass
            elif token in [12]:
                self.enterOuterAlt(localctx, 2)
                self.state = 67
                localctx.Pattern = self.patternIdentifier()
                pass
            else:
                raise NoViableAltException(self)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class SelectionIdentifierContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser
            self.Basic = None # BasicIdentifierContext

        def basicIdentifier(self):
            return self.getTypedRuleContext(SigmaParser.BasicIdentifierContext,0)


        def getRuleIndex(self):
            return SigmaParser.RULE_selectionIdentifier

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterSelectionIdentifier" ):
                listener.enterSelectionIdentifier(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitSelectionIdentifier" ):
                listener.exitSelectionIdentifier(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitSelectionIdentifier" ):
                return visitor.visitSelectionIdentifier(self)
            else:
                return visitor.visitChildren(self)




    def selectionIdentifier(self):

        localctx = SigmaParser.SelectionIdentifierContext(self, self._ctx, self.state)
        self.enterRule(localctx, 18, self.RULE_selectionIdentifier)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 70
            localctx.Basic = self.basicIdentifier()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class PatternIdentifierContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser
            self.Wildcard = None # WildcardIdentifierContext

        def wildcardIdentifier(self):
            return self.getTypedRuleContext(SigmaParser.WildcardIdentifierContext,0)


        def getRuleIndex(self):
            return SigmaParser.RULE_patternIdentifier

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterPatternIdentifier" ):
                listener.enterPatternIdentifier(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitPatternIdentifier" ):
                listener.exitPatternIdentifier(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitPatternIdentifier" ):
                return visitor.visitPatternIdentifier(self)
            else:
                return visitor.visitChildren(self)




    def patternIdentifier(self):

        localctx = SigmaParser.PatternIdentifierContext(self, self._ctx, self.state)
        self.enterRule(localctx, 20, self.RULE_patternIdentifier)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 72
            localctx.Wildcard = self.wildcardIdentifier()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class BasicIdentifierContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser
            self.Identifier = None # Token

        def IDENTIFIER(self):
            return self.getToken(SigmaParser.IDENTIFIER, 0)

        def getRuleIndex(self):
            return SigmaParser.RULE_basicIdentifier

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterBasicIdentifier" ):
                listener.enterBasicIdentifier(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitBasicIdentifier" ):
                listener.exitBasicIdentifier(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitBasicIdentifier" ):
                return visitor.visitBasicIdentifier(self)
            else:
                return visitor.visitChildren(self)




    def basicIdentifier(self):

        localctx = SigmaParser.BasicIdentifierContext(self, self._ctx, self.state)
        self.enterRule(localctx, 22, self.RULE_basicIdentifier)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 74
            localctx.Identifier = self.match(SigmaParser.IDENTIFIER)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class WildcardIdentifierContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser
            self.Identifier = None # Token

        def WILDCARD(self):
            return self.getToken(SigmaParser.WILDCARD, 0)

        def getRuleIndex(self):
            return SigmaParser.RULE_wildcardIdentifier

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterWildcardIdentifier" ):
                listener.enterWildcardIdentifier(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitWildcardIdentifier" ):
                listener.exitWildcardIdentifier(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitWildcardIdentifier" ):
                return visitor.visitWildcardIdentifier(self)
            else:
                return visitor.visitChildren(self)




    def wildcardIdentifier(self):

        localctx = SigmaParser.WildcardIdentifierContext(self, self._ctx, self.state)
        self.enterRule(localctx, 24, self.RULE_wildcardIdentifier)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 76
            localctx.Identifier = self.match(SigmaParser.WILDCARD)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx





