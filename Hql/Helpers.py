from __future__ import annotations
import logging, time
from typing import TYPE_CHECKING, Optional, Union

if TYPE_CHECKING:
    from Hql.Data import Data
    from Hql.Config import Config
    from Hql.Context import Context

def can_thread():
    import sys
    if hasattr(sys, '_is_gil_enabled') and not sys._is_gil_enabled():
        return True
    return False

def run_query(text:str, conf:Config, name:str='', ctx:Optional[Context]=None, **kwargs) -> Union[Data, str]:
    from Hql.Exceptions import HqlExceptions as hqle
    from Hql.Exceptions import HacExceptions as hace
    from Hql.Parser import Parser
    from Hql.Parser.Sigma import SigmaParser
    from Hql.Compiler import HqlCompiler
    from Hql.Hac.Parser import Parser as HaCParser
    from Hql.Query import Query
    from Hql.Hac import Hac

    ##################################
    ## Generate HaC (if applicable) ##
    ##################################

    logging.debug(f'Parsing HaC for {name}...')

    parser = None

    try:
        logging.info('Attempting Sigma')
        parser = SigmaParser(text, conf)
        hac = parser.gen_hac()
    except Exception as e:
        logging.warning(e)
        logging.info('Failed Sigma, using Hql')
        # We're just skipping over to HaC Parsing then
        try:
            hac = HaCParser.parse_text(text, name)
        except (hace.LexerException, hace.HacException):
            hac = None

    if kwargs.get('render_hac', ''):
        if not hac:
            logging.critical('Hql file does not contain a valid HaC comment!')
            return ''

        return hac.render(kwargs['render_hac'])

    #######################
    ## Generate Assembly ##
    #######################
    
    logging.debug(f'Parsing {name}...')
    start = time.perf_counter()

    if not parser:
        parser = Parser(text)
    parser.assemble()
    
    logging.debug('Done.')
    
    end = time.perf_counter()
    logging.debug(f'Parsing took {end - start}')
    
    if kwargs.get('asm_show', False):
        # Use print to give a raw output
        return str(parser.assembly)

    if kwargs.get('deparse', False) or kwargs.get('init_hac', False):
        deparse = ''

        if kwargs.get('init_hac'):
            hac = Hac({}, src='init')

        if hac:
            deparse += hac.render(target='decompile')
            deparse += '\n'

        if not isinstance(parser.assembly, Query):
            raise hqle.CompilerException(f'Attempting to compile non-Query assembly {type(parser.assembly)}')

        deparse += parser.assembly.deparse()
        return deparse
        
    ######################
    ## Compile Assembly ##
    ######################
    
    logging.debug("Compiling...")
    start = time.perf_counter()

    if not isinstance(parser.assembly, Query):
        raise hqle.CompilerException(f'Attempting to compile non-Query assembly {type(parser.assembly)}')
    
    compiler = HqlCompiler(conf, parser.assembly, hac=hac)
    
    # second pass
    # assert compiler.root
    # compiler.root = compiler.root.recompile(conf)
    
    end = time.perf_counter()
    logging.debug("Done.")
    
    logging.debug(f"Compiling took {end - start}")

    if kwargs.get('plan', False):
        assert compiler.root
        return compiler.root.render()

    # if kwargs.get('decompile:
    #     return compiler.decompile()
   
    if kwargs.get('no_exec', False):
        return ''
    
    #############
    ## Queries ##
    #############

    logging.debug("Running")
    start = time.perf_counter()
    
    results = compiler.run(ctx=ctx).data
   
    end = time.perf_counter() 
    logging.debug("Ran")
    logging.debug(f"Computation took {end - start}")
    
    logging.debug(f'Got {len(results)} results from query')
    
    return results
