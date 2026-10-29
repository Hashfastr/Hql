from __future__ import annotations
from . import Database
from Hql.Exceptions import HqlExceptions as hqle
from Hql.Data import Data
from Hql.Context import register_database, Context

'''
Static DB, just give it a data object and it'll act like a Database.
Not much else to it.
'''
# @register_database('Static')
class Static(Database):
    def __init__(self, data:Data):
        Database.__init__(self, dict())
        self.data = data
     
    # Executed as an instruction, so has to give back a Context like other databases
    def eval(self, ctx: Context, **kwargs) -> Context:
        ctx = ctx.copy()
        ctx.data = self.data
        return ctx
