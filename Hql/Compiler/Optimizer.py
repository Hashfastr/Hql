from __future__ import annotations
from typing import TYPE_CHECKING, Optional, Sequence, Union

if TYPE_CHECKING:
    from Hql.Operators import Operator
    from Hql.Compiler import BranchDescriptor, InstructionSet

class Optimizer:
    def __init__(self, isets:InstructionSet) -> None:
        self.isets = isets



    '''
    def optimize(self, ops: Sequence[Union[Operator, BranchDescriptor]]) -> list[BranchDescriptor]:
        new = []
        for i in ops:
            if isinstance(i, Operators.Operator):
                acc, _ = self.compile(i)
                assert isinstance(acc, BranchDescriptor)
                new.append(acc)
            else:
                new.append(i)
        ops = new
        
        logging.debug(f'Optimizing the following operators:')
        for op in ops:
            logging.debug(f'    {op.get_op().id}: {op.get_op().type}')
        
        optimized = [ops[0]]
        for op in ops[1:]:
            i = -1
            while i >= -len(optimized):
                if not (optimized[i].get_attr('row_dependent') or optimized[i].get_attr('row_mutable')) and op.get_attr('row_reducing'):
                    if isinstance(optimized[i].get_op(), Operators.Take) or isinstance(op.get_op(), Operators.Take):
                        logging.debug("Holding take's location")
                        break

                    if type(optimized[i].get_op()) == type(op.get_op()):
                        break

                    if optimized[i].get_attr('requires_sync') and isinstance(op.get_op(), Operators.Take):
                        break

                    if optimized[i].get_attr('type_casting'):
                        break

                    can_map, mapped = self.apply_map(optimized[i], op)
                    if can_map == 1:
                        op = mapped
                        logging.debug(f'{op.get_op().id} is remapped by {optimized[i].get_op().id}')
                        i -= 1
                        continue

                    if can_map == 2:
                        logging.debug(f'{op.get_op().id} references names provided by {optimized[i].get_op().id}')
                        break

                    logging.debug(f'Can optimize {op.get_op().id} passing {optimized[i].get_op().id}')
                    i -= 1
                    continue

                else:
                    logging.debug(f'As high as we can go for {op.get_op().id}')
                    break
            
            if i == -1:
                optimized.append(op)
            else:
                optimized.insert(i+1, op)
        
        logging.debug('Final optimized set:')
        for op in optimized:
            logging.debug(f'    {op.get_op().id}: {op.get_op().type}')

        return optimized
    '''
