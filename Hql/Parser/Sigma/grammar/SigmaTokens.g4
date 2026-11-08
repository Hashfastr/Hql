lexer grammar SigmaTokens;

AND : 'and' ;
OR : 'or' ;
NOT : 'not' ;
OF : 'of' ;
ALL : 'all' ;
THEM : 'them' ;

LP : '(' ;
RP : ')' ;
ASTERISK : '*' ;

INT : ('0'..'9')+ ;

IDENTIFIER : ('a'..'z' | 'A'..'Z' | '0'..'9' | '.' | '_' | '-')+ ;
WILDCARD : ('a'..'z' | 'A'..'Z' | '0'..'9' | '.' | '_' | '-' | '*')+ ;
// REGEXIDENTIFIER : ('a'..'z' | 'A'..'Z' | '0'..'9' | '.' | '+' | '[' | ']' | '(' | ')' | '*' | '-' | '?')+ ;

WHITESPACE:
    (
          '\t'
        | ' '
        | '\r'
        | '\n'
        | '\f'
        | '\u00a0'
        | '\u1680'
        | '\u180e'
        | '\u2000'
        | '\u2001'
        | '\u2002'
        | '\u2003'
        | '\u2004'
        | '\u2005'
        | '\u2006'
        | '\u2007'
        | '\u2008'
        | '\u2009'
        | '\u200a'
        | '\u200b'
        | '\u202f'
        | '\u205f'
        | '\u3000'
        | '\ufeff'
    )+ 
    -> channel(HIDDEN);
