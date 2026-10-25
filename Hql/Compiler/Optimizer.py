from __future__ import annotations
from typing import TYPE_CHECKING, Optional, Sequence, Union

if TYPE_CHECKING:
    from Hql.Operators import Operator
    from Hql.Compiler import BranchDescriptor

class :
    def __init__(self, operators:Sequence[Operator | BranchDescriptor] | None=None) -> None:
        branches:list[BranchDescriptor] = []

        self.operators = operators if operators is not None else []

    # def optimize(self, )
