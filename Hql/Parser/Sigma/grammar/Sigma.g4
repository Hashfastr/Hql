grammar Sigma;

import SigmaTokens;

// EOF so trailing text the grammar can't match is a syntax error, not silently dropped
condition:
      Statement=orStatement EOF;

orStatement:
      Left=andStatement (OR Right+=andStatement)*;
    
andStatement:
      Left=statement (AND Right+=statement)*;

statement:
      ofStatement
    | notStatement
    | bracketStatement
    | selectionIdentifier
    ;
    
notStatement:
    NOT Statement=statement;

bracketStatement:
    LP Statement=orStatement RP;
    
ofStatement:
    Specifier=ofSpecifier OF Target=ofTarget;
    
ofSpecifier:
      Int=INT
    | All=ALL
    ;

ofTarget:
      Them=THEM
    | Pattern=patternIdentifier
    ;

selectionIdentifier:
      Basic=basicIdentifier;
      
patternIdentifier: Wildcard=wildcardIdentifier;
    
basicIdentifier:
    Identifier=IDENTIFIER;
    
wildcardIdentifier:
    Identifier=WILDCARD;
    
// regexIdentifier:
//     Identifier=REGEXIDENTIFIER;
