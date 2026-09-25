from __future__ import annotations
from typing import TYPE_CHECKING, Union, Optional
import logging
import random
import datetime, time
from pathlib import Path

from Hql.Exceptions import HqlExceptions as hqle
from Hql.Context import Context
from Hql.Data import Data

if TYPE_CHECKING:
    from Hql.Cache import Cache
    from Hql.Config import Config
    from Hql.Database import Database
    from Hql.Compiler import InstructionSet
    from Hql.Hac.Engine import Detection

class QueryPool():
    """Manage a collection of asynchronously executed HQL queries."""

    def __init__(self, auto_run:bool=True, cache:Optional[Cache]=None) -> None:
        from threading import Semaphore
        self.auto_run = auto_run
        self.pool:list[QueryThread] = []
        self.semaphore = Semaphore()
        self.ctx = Context(Data(), cache=cache)

    def add_query(self, text:str, config:Config, name:str='', **kwargs) -> None:
        t = QueryThread(text, config, name=name, ctx=self.ctx.fork(), **kwargs)
        if self.auto_run:
            t.start()
        self.pool.append(t)

    def is_idle(self) -> bool:
        return not self.pool

    def start(self):
        for t in self.pool:
            if not t.started:
                t.start()

    # Gets completed threads and frees them from the pool
    def get_completed(self) -> list[QueryThread]:
        completed = []
        for t in list(self.pool):
            if not t.is_alive():
                t.join()
                completed.append(t)
                self.pool.remove(t)
        if self.is_idle():
            self.ctx.cache.write_back()
        return completed

class QueryThread():
    """Execute one HQL query synchronously or in a worker thread."""

    def __init__(self, text:str, config:Config, name:str='', ctx:Optional[Context]=None, **kwargs) -> None:
        from copy import deepcopy
        from Hql.Data import Data
        from Hql.Helpers import can_thread

        self.text = text
        self.config = deepcopy(config)
        self.name = name
        self.threaded = can_thread()
        self.kwargs = kwargs
        self.ctx = ctx if ctx is not None else Context(Data())

        self.started = False
        self.thread = None
        self._output = Data()
        self.compiled:str = ''
        self.failed = False

    @property
    def output(self) -> Data:
        return self._output

    @output.setter
    def output(self, val:Data):
        from Hql.Data import Data
        if not isinstance(val, Data):
            raise hqle.CompilerException(f'QueryThread got an invalid output of type {type(val)} expecting Data')
        self._output = val

    # Starts the thread and sets values in the class
    def start(self) -> None:
        self.started = True

        if not self.threaded:
            self.run()
            return

        from threading import Thread
        self.thread = Thread(name=self.name, target=self.run, args=())
        self.thread.start()

    # Runs the query, function that is threaded
    def run(self) -> None:
        from Hql.Helpers import run_query
        try:
            output = run_query(
                self.text,
                self.config,
                name=self.name,
                ctx=self.ctx,
                **self.kwargs,
            )

            if isinstance(output, str):
                self.compiled = output
            else:
                self.output = output

        except Exception as e:
            import traceback
            self.traceback = {
                'traceback': traceback.format_exc(),
                'exception': str(e)
            }
            self.failed = True
        finally:
            self.ctx.cache.write_back()

    def is_alive(self) -> bool:
        if not self.thread or not self.threaded:
            return False
        return self.thread.is_alive()

    def join(self) -> Union[Data, str, None]:
        if self.threaded and self.thread:
            self.thread.join()
        return self.output

class InstructionPool():
    """Manage concurrent execution of compiled instructions."""

    def __init__(self, auto_run:bool=True) -> None:
        from threading import Semaphore
        self.auto_run = auto_run
        self.pool:list[InstructionThread] = []
        self.semaphore = Semaphore()

    def add_instruction(self, inst:Union[InstructionSet, Database], ctx:Context) -> None:
        t = InstructionThread(inst, ctx)
        if self.auto_run:
            t.start()
        self.pool.append(t)

    def is_idle(self) -> bool:
        return not self.pool

    def start(self):
        # Don't thread if we don't need to
        if len(self.pool) == 1:
            instid = self.pool[0].id
            logging.debug(f'No need to thread {instid}, only one instruction in the pool')
            self.pool[0].run()
            return

        for t in list(self.pool):
            if not t.started:
                t.start()

    # Gets completed threads and frees them from the pool
    def get_completed(self) -> list[InstructionThread]:
        completed = []
        for t in self.pool:
            if not t.is_alive():
                t.join()
                completed.append(t)
                self.pool.remove(t)
        return completed

class InstructionThread():
    """Execute one instruction set or database operation."""

    def __init__(self, inst:Union[InstructionSet, Database], ctx:Context) -> None:
        from Hql.Helpers import can_thread

        self.threaded = can_thread()

        self.inst = inst
        self.ctx = ctx
        self.started = False
        self.thread = None
        self._output:Optional[Context] = None
        self.id = self.inst.id

    @property
    def output(self) -> Optional[Context]:
        return self._output

    @output.setter
    def output(self, val:Optional[Context]):
        from Hql.Context import Context
        if not isinstance(val, (type(None), Context)):
            raise hqle.CompilerException(f'InstructionThread got an invalid output of type {type(val)} expecting Optional[Context]')
        self._output = val

    # Starts the thread and sets values in the class
    def start(self) -> None:
        if not self.threaded:
            self.run()
            return

        from threading import Thread
        self.thread = Thread(name=self.inst.id, target=self.run, args=())
        self.thread.start()

    # Runs the query, function that is threaded
    def run(self) -> None:
        try:
            self.output = self.inst.eval(self.ctx)
        finally:
            self.ctx.cache.write_back()

    def is_alive(self) -> bool:
        if not self.thread or not self.threaded:
            return False
        return self.thread.is_alive()

    def join(self) -> Optional[Context]:
        if self.threaded and self.thread:
            self.thread.join()
        return self.output

class HacPool():
    """Queue and run HQL analytic detections with bounded concurrency."""

    def __init__(self, auto_run:bool=True, max_threads:int=16) -> None:
        from threading import Semaphore
        from Hql.Data import Data

        self.auto_run = auto_run
        self.pool:list[HacThread] = []
        self.queue:list[HacThread] = []
        self.max_threads = max_threads
        self.semaphore = Semaphore(max_threads)

        self.completed:list[HacThread] = []
        self.max_retained = 1000

        self.ctx = Context(Data())

    def get_by_id(self, tid:str):
        for i in self.pool + self.completed + self.queue:
            if i.id == tid:
                return i
        return None

    def get_runs(self):
        runs = []
        for i in self.pool:
            runs.append({
                'run_id': i.id,
                'run_date': i.run_date.isoformat(),
                'started': i.started,
                'failed': i.failed,
                'completed': i.completed
            })
        return runs

    def add_detection(self, detection:Detection, query_now:Optional[datetime.datetime]=None) -> str:
        t = HacThread(detection, query_now=query_now, ctx=self.ctx.fork())
        if self.auto_run and self.semaphore.acquire(blocking=False):
            logging.debug(f'{t.id} started execution')
            t.start()
            self.pool.append(t)
        else:
            logging.debug(f'{t.id} queued for execution')
            self.queue.append(t)

        return t.id

    def write_detections(self, path:Path):
        for i in self.pool:
            tid = i.id
            txt = i.detection.txt
            with open(path/f'{tid}.log', mode='w+') as f:
                f.write(txt)

    def is_idle(self) -> bool:
        return not self.pool

    def is_overloaded(self) -> bool:
        return len(self.queue) > self.max_threads

    def clear_queue(self):
        count = 0
        for t in self.queue:
            if self.semaphore.acquire(blocking=False):
                self.pool.append(t)
                self.queue.remove(t)
                t.start()
                count += 1
            else:
                break
        if count:
            logging.debug(f'Moved {count} detections from queue to running')

    def gather_threads(self):
        def join_thread(t:HacThread):
            if not t.is_alive():
                t.join()
                self.pool.remove(t)
                self.semaphore.release()

                if len(self.completed) >= self.max_retained:
                    self.completed = self.completed[1:]
                self.completed.append(t)
                self.ctx.cache.merge(t.ctx.cache)
        
        for t in self.pool:
            try:
                join_thread(t)
            except Exception as e:
                logging.error('Could not join thread')
                logging.error(e)

                self.pool.remove(t)
                self.semaphore.release()

    def get_completed(self) -> list[HacThread]:
        completed = self.completed
        self.completed = []
        return completed

class HacThread():
    """Execute one HQL analytic detection and retain its run metadata."""

    def __init__(self, detection:Detection, query_now:Optional[datetime.datetime]=None, ctx:Optional[Context]=None) -> None:
        from Hql.Helpers import can_thread
        from Hql.Data import Data

        self.threaded = can_thread()

        self.query_now = query_now if query_now else datetime.datetime.now()
        self.detection = detection

        self.started = False
        self.completed = False
        self.thread = None
        self._output:Data = Data()
        self.failed = False
        self.num_results = 0

        self.id = '%08x' % random.getrandbits(32)
        self.run_date = datetime.datetime.now()
        self.duration = 0

        self.ctx = ctx if ctx is not None else Context(Data())

    @property
    def output(self) -> Data:
        return self._output

    @output.setter
    def output(self, val:Data):
        if not isinstance(val, Data):
            raise hqle.CompilerException(f'HacThread got an invalid input of type {type(val)} expecting Context')
        self._output = val

    def to_dict(self):
        d = {
            'run_id': self.id,
            'run_date': self.run_date.isoformat(),
            'started': self.started,
            'duration': self.duration,
            'failed': self.failed,
            'completed': self.completed,
            'num_results': self.num_results
        }

        if self.detection.hac:
            d['hac'] = self.detection.hac.asm

        # On failure self.output is the traceback string, not a Context
        d['results'] = self.output.to_dict()
        # d['str_out'] = self.compiled
        return d

    # Starts the thread and sets values in the class
    def start(self) -> None:
        self.started = True
        logging.info(f'Starting detection {self.detection.id}')

        if not self.threaded:
            self.run()
            return

        from threading import Thread
        self.thread = Thread(name=self.detection.id, target=self.run, args=())
        self.thread.start()

    # Runs the query, function that is threaded
    def run(self) -> None:
        from Hql.Data import Data
        try:
            start = time.perf_counter()
            self.output = self.detection.run(self.query_now, ctx=self.ctx).data
            end = time.perf_counter()
            
            self.duration = end - start
            self.completed = True
            self.num_results = len(self.output) if isinstance(self.output, Data) else 0

            logging.info(f'{self.detection.id} - {len(self.output)} results')
        except Exception as e:
            import traceback
            logging.critical(e)
            logging.critical(traceback.format_exc())
            self.failed = True
        finally:
            self.ctx.cache.write_back()

    def is_alive(self) -> bool:
        if not self.thread or not self.threaded:
            return False
        return self.thread.is_alive()

    def join(self) -> Data:
        if self.threaded and self.thread:
            self.thread.join()
        return self.output
