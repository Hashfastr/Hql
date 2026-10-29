from __future__ import annotations

from typing import Optional, TYPE_CHECKING, Union

from Hql.Context import register_func
from Hql.Exceptions import HqlExceptions as hqle
from Hql.Functions import Function

if TYPE_CHECKING:
    from Hql.Expressions.Literals import StringLiteral
    from Hql.Expressions import Expression
    from Hql.Context import Context

'''
Helpers shared by the base64 functions.
Only static (literal) values are supported, field references are left as is.
'''
def resolve_args(func, ctx:Context) -> tuple[Optional[StringLiteral], str]:
    from Hql.Expressions.Literals import StringLiteral

    val = func.val.preprocess(ctx)
    enc = func.enc.preprocess(ctx)

    if not isinstance(enc, StringLiteral):
        raise hqle.ArgumentException(f'{func.name} encoding value did not resolve to a StringLiteral: {enc}')

    if not isinstance(val, StringLiteral):
        return None, enc.str()

    return val, enc.str()

def encode(func, val:StringLiteral, enc:str) -> bytes:
    # val.value is the raw utf-8, val.str() would give the escaped form
    try:
        return val.value.decode('utf-8').encode(enc)
    except (UnicodeError, LookupError) as e:
        raise hqle.ArgumentException(f'{func.name} could not encode {val.str()!r} as {enc}: {e}')

def eval_static(func, ctx:Context) -> object:
    from Hql.Expressions.Literals import Literal

    res = func.preprocess(ctx)
    if not isinstance(res, Literal):
        raise hqle.CompilerException(f'{func.name} is only implemented for static string values')

    return func.broadcast(ctx, res)

@register_func('base64')
@register_func('b64')
class base64enc(Function):
    """Encode a string as Base64 using the requested character encoding."""

    def __init__(self, args: list, conf:Optional[dict]=None):
        from Hql.Expressions.Literals import StringLiteral
        from Hql.Expressions.References import Reference
        Function.__init__(self, args, 1, 2, conf=conf)

        for i in args:
            if not isinstance(i, (StringLiteral, Reference)):
                raise hqle.ArgumentException(f'Invalid argument type {type(i)} passed to {self.name}')
            
        self.val:Union[StringLiteral, Reference] = args[0]
        self.enc = args[1] if len(args) == 2 else StringLiteral('ascii')

    def preprocess(self, ctx: Context, receiver=None) -> object:
        from Hql.Expressions.Literals import StringLiteral

        from base64 import b64encode

        val, enc = resolve_args(self, ctx)
        if val is None:
            return self

        return StringLiteral(b64encode(encode(self, val, enc)).decode())

    def eval(self, ctx: Context, receiver=None) -> object:
        return eval_static(self, ctx)

@register_func('base64dec')
@register_func('b64dec')
class base64dec(Function):
    """Decode a Base64 string using the requested character encoding."""

    def __init__(self, args:list, conf:Optional[dict]=None):
        from Hql.Expressions.Literals import StringLiteral
        from Hql.Expressions.References import Reference
        Function.__init__(self, args, 1, 2, conf=conf)

        for i in args:
            if not isinstance(i, (StringLiteral, Reference)):
                raise hqle.ArgumentException(f'Invalid argument type {type(i)} passed to {self.name}')
            
        self.val:Union[StringLiteral, Reference] = args[0]
        self.enc = args[1] if len(args) == 2 else StringLiteral('ascii')

    def preprocess(self, ctx: Context, receiver=None) -> object:
        from base64 import b64decode
        from binascii import Error as B64Error
        from Hql.Expressions.Literals import StringLiteral

        val, enc = resolve_args(self, ctx)
        if val is None:
            return self

        try:
            raw = b64decode(val.value, validate=True)
            return StringLiteral(raw.decode(enc))
        except (B64Error, UnicodeError, LookupError) as e:
            raise hqle.ArgumentException(f'{self.name} could not decode {val.str()!r} as {enc}: {e}')
       
    def eval(self, ctx: Context, receiver=None) -> object:
        return eval_static(self, ctx)

@register_func('base64offset')
@register_func('base64off')
@register_func('b64off')
class base64off(Function):
    """Generate Base64 fragments for each possible byte alignment."""

    def __init__(self, args: list, conf:Optional[dict]=None):
        from Hql.Expressions.Literals import StringLiteral
        from Hql.Expressions.References import Reference
        Function.__init__(self, args, 1, 2, conf=conf)

        for i in args:
            if not isinstance(i, (StringLiteral, Reference)):
                raise hqle.ArgumentException(f'Invalid argument type {type(i)} passed to {self.name}')
            
        self.val:Union[StringLiteral, Reference] = args[0]
        self.enc = args[1] if len(args) == 2 else StringLiteral('ascii')

    def calc_offset(self, raw:bytes) -> list[StringLiteral]:
        from base64 import b64encode
        from Hql.Expressions.Literals import StringLiteral
        
        start_offsets = (0, 2, 3)
        end_offsets = (None, -3, -2)

        # Offsets are based on the encoded byte length, not characters
        parts = []
        for i in range(3):
            part = b64encode(i * b" " + raw)[
                start_offsets[i] : end_offsets[(len(raw) + i) % 3]
            ].decode()
            parts.append(StringLiteral(part))

        return parts

    def preprocess(self, ctx: Context, receiver=None) -> object:
        from Hql.Expressions.Literals import Multivalue

        val, enc = resolve_args(self, ctx)
        if val is None:
            return self

        return Multivalue(self.calc_offset(encode(self, val, enc)))
       
    def eval(self, ctx: Context, receiver=None) -> object:
        return eval_static(self, ctx)
