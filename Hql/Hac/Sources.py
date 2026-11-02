from __future__ import annotations
from fnmatch import fnmatch
from Hql.Exceptions import HqlExceptions as hqle
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from Hql.Compiler.InstructionSet import InstructionSet
    from Hql.Context import Context

'''
Resolves product/service/category selections against the classes in scope

class windows = {
    let process_creation = Sysmon
    | where EventID == 1
    ;
};
product('windows').category('process_creation')

Resolves to windows.process_creation. The selections are walked as nested
class members in the order product.service.category, unselected parts are
skipped. Without a product every class in scope is searched.
'''
class Source():
    def __init__(self, ctx:Context) -> None:
        self.ctx = ctx
        self.products:list[str] = []
        self.services:list[str] = []
        self.categories:list[str] = []

    def preprocess(self, ctx:Context) -> InstructionSet:
        from Hql.Compiler import InstructionSet

        isets = []
        for i in self.gen_products(ctx):
            if self.services:
                i.service(self.services)
            if self.categories:
                i.category(self.categories)
            isets += i.preprocess()

        # A category on its own falls back to a top level let of the same name
        if not isets and self.categories and not self.products and not self.services:
            for name, value in ctx.symbol_table.items():
                iset = Product.tabular(value)
                if iset and any(fnmatch(self.symbol_name(name), x) for x in self.categories):
                    isets.append(iset)

        if not isets:
            raise hqle.QueryException(f'No source resolved for {self.deparse_path()}')

        if len(isets) == 1:
            return isets[0]

        return InstructionSet(isets)

    def gen_products(self, ctx:Context) -> list[Product]:
        patterns = self.products if self.products else ['*']

        products = []
        for name, value in ctx.symbol_table.items():
            # classes are stored as a dict namespace of their members
            if not isinstance(value, dict):
                continue

            name = self.symbol_name(name)
            if any(fnmatch(name, x) for x in patterns):
                products.append(Product(name, value, ctx))
        return products

    @staticmethod
    def symbol_name(key:object) -> str:
        from Hql.Expressions.References import NamedReference
        return key.name if isinstance(key, NamedReference) else str(key)

    def deparse_path(self) -> str:
        parts = []
        for i in (self.products if self.products else ['*'], self.services, self.categories):
            if not i:
                continue
            parts.append(i[0] if len(i) == 1 else '(' + ', '.join(i) + ')')
        return '.'.join(parts)

    def product(self, pattern:str) -> Source:
        self.products.append(pattern)
        return self

    def service(self, pattern:str) -> Source:
        self.services.append(pattern)
        return self

    def category(self, pattern:str) -> Source:
        self.categories.append(pattern)
        return self

class Product():
    def __init__(self, name:str, namespace:dict, ctx:Context) -> None:
        self.name = name
        self.ctx = ctx
        # Current selection of class members, keyed by their dotted path
        self.nodes:dict[str, object] = {name: namespace}

    def preprocess(self) -> list[InstructionSet]:
        isets = []
        for i in self.nodes.values():
            # A class left unnarrowed selects all its tabular members
            if isinstance(i, dict):
                members = [i[x] for x in i if not x.startswith('_')]
            else:
                members = [i]

            for j in members:
                iset = self.tabular(j)
                if iset:
                    isets.append(iset)
        return isets

    @staticmethod
    def tabular(node:object) -> Optional[InstructionSet]:
        from Hql.Compiler import InstructionSet
        from Hql.Database import Database

        if isinstance(node, InstructionSet):
            return node
        if isinstance(node, Database):
            return InstructionSet(node, node.preamble.pipes)
        return None

    def narrow(self, patterns:list[str]) -> Product:
        nodes = {}
        for path, node in self.nodes.items():
            if not isinstance(node, dict):
                continue

            for i in node:
                if any(fnmatch(i, x) for x in patterns):
                    nodes[f'{path}.{i}'] = node[i]

        self.nodes = nodes
        return self

    def service(self, patterns:list[str]) -> Product:
        return self.narrow(patterns)

    def category(self, patterns:list[str]) -> Product:
        return self.narrow(patterns)
