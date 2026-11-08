import sys
from Hql.Config import Config
from Hql.Data import Data
from Hql.Threading import QueryPool
from Hql.Hac.Engine import HacEngine
from Hql.Helpers import config_logging

import json
import time
import logging
import argparse, sys
import cProfile, pstats
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(prog=sys.argv[0])
    parser.add_argument('-asm', '--asm-show', help='Show the json of the parsed data and exit', action='store_true')
    file_ops = parser.add_mutually_exclusive_group(required=True)
    file_ops.add_argument('-f', '--file', help="Hql/Sigma file")
    file_ops.add_argument('-d', '--directory', help="File to compile")
    parser.add_argument('-o', '--output', help='Output dir otherwise stdout')
    parser.add_argument('-v', '--verbose', help="Set verbosity to debug", action='store_true')
    parser.add_argument('-l', '--logging-level', help="Verbosity level 1-5, where 5 is debug, 1 is critical, default is 3, warning.", type=int)
    parser.add_argument('-p', '--profile', help="Profile the performance of Hql", action='store_true')
    parser.add_argument('-c', '--config', help="Location of the config file")
    parser.add_argument('-nx', '--no-exec', help="Only compile, don't execute", action='store_true')
    parser.add_argument('-dpar', '--deparse', help="Deparse the program before compiling", action='store_true')
    # parser.add_argument('-dec', '--decompile', help="Decompile the program before running", action='store_true')
    parser.add_argument('-pl', '--plan', help="Prints the plan for the execution", action='store_true')
    parser.add_argument('-hac', '--render-hac', help="Renders HaC to a given format (md, json, decompile)")
    parser.add_argument('--init-hac', help="Adds a hac comment and deparses", action='store_true')
    parser.add_argument('-eng', '--hac-engine', help="Runs as the hac engine", action='store_true')
    parser.add_argument('--compile', help='Compile to a given target', action='store_true')
    
    args = parser.parse_args()
    
    profiler = None
    if args.profile:
        profiler = cProfile.Profile()
        profiler.enable()
    
    if args.logging_level:
        config_logging(args.logging_level)
    elif args.verbose:
        config_logging(5)
    else:
        config_logging(4)
        
    if args.config == None:
        conf_path = "./conf"
    else:
        conf_path = args.config
    
    if args.hac_engine:
        if args.directory:
            engine = HacEngine(Path(args.directory), True, Path(conf_path))
        else:
            engine = HacEngine(Path(args.file), False, Path(conf_path))

        engine.run()
        return
    
    conf = Config(Path(conf_path))

    '''
    Loading files
    '''
    files:list[Path] = []
    if args.directory:
        path = Path(args.directory)

        # Hql
        for file in path.rglob('*.hql'):
            if file.is_file():
                files.append(file)

        # yml
        for file in path.rglob('*.yml'):
            if file.is_file():
                files.append(file)

    else:
        files.append(Path(args.file))

    errors = []
    successes = []
    
    pool = QueryPool()
    kwargs = vars(args)
    kwargs.pop('config')

    '''
    Run query files
    '''
    for i in files:
        with i.open(mode='r') as f:
            txt = f.read()
        pool.add_query(txt, conf, name=str(i), **kwargs)

    '''
    Sync and get output
    '''
    while not pool.is_idle():
        completed = pool.get_completed()

        for i in completed:
            if i.failed:
                errors.append(i.name)
            else:
                successes.append(i.name)

            if isinstance(i.output, Data):
                print(json.dumps(i.output.to_dict(), indent=2))
            elif isinstance(i.output, str):
                print(i.output)
            
        time.sleep(0.1)

    for i in errors:
        logging.error(f'Failed executing {i}')
    logging.info(f'Finished execution {len(errors)} errors, {len(successes)} successes')
    
    #####################
    ## Profiling stuff ##
    #####################
    
    if args.profile:
        assert profiler
        profiler.disable()
        
        with open('./profile.txt', mode='w+') as f:
            stats = pstats.Stats(profiler, stream=f)
            stats.sort_stats('time')
            stats.print_stats()
            
        logging.info("Performance metrics outputted to profile.txt")

    if errors:
        return -1

if __name__ == "__main__":
    main()
