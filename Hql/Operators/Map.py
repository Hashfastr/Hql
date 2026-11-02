from __future__ import annotations
from Hql.Operators.Operator import Operator

from typing import TYPE_CHECKING, Sequence, Union

if TYPE_CHECKING:
    from Hql.Expressions.References import Reference
    from Hql.Query import Mapping
    from Hql.Context import Context
    from Hql.Expressions import Expression

'''
Applies a mapping, to a dataset, can be a compiler directive or passed to a backend.

map ecs = { EventID: event.id };
syslog-*
| map ecs
| where EventID == 4624

Parsed with the names of the mappings, the compiler resolves those names to
the Mapping statements. When added to an InstructionSet the following
operators are remapped and the results are renamed back.
'''
class Map(Operator):
    """Apply named field mappings to the operators that follow."""

    def __init__(self, mapping:Union[Mapping, Reference, Sequence[Union[Mapping, Reference]]]):
        Operator.__init__(self)
        self.maps:list[Union[Mapping, Reference]] = list(mapping) if isinstance(mapping, (list, tuple)) else [mapping]

    @property
    def exprs(self) -> Sequence[Expression]:
        """The exprs property."""
        return self.maps

    @exprs.setter
    def exprs(self, value) -> None:
        self.maps = list(value)

    @property
    def names(self) -> list[Reference]:
        from Hql.Query import Mapping
        return [x.name if isinstance(x, Mapping) else x for x in self.maps]

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'type': self.type,
            'maps': [x.str() for x in self.names]
        }

    def deparse(self) -> str:
        return 'map ' + ', '.join([x.deparse() for x in self.names])

    # Meta operator, consumed by the InstructionSet it's added to
    def eval(self, ctx:Context) -> Context:
        return ctx
