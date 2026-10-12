from __future__ import annotations
from typing import TYPE_CHECKING, Optional, TypeAlias, Any
from datetime import datetime
from threading import Lock
import logging
import sys

from Hql.Data import Data

CacheEntry: TypeAlias = (
    tuple[int, str, Optional[datetime], Data, bool]
    | tuple[None, None, None, None, None]
)

'''
Implements a hash-table that refers to a dataset
'''
class Cache():
    def __init__(self, table_size:int=4096, parent:Optional[Cache]=None):
        self.table_size = table_size
        self.parent = parent

        '''
        Using this for locking

        with lock:
            ...
        '''
        self.lock = Lock()

        # Original hashmap size, key, datetime, dataset, dirty flag
        self._data:list[CacheEntry] = [(None, None, None, None, None) for _ in range(self.table_size)]

    def __len__(self) -> int:
        count = 0
        for i in self._data:
            if i[0] is not None:
                count += 1
        return count

    def __deepcopy__(self, memo:dict[int, Any]) -> Cache:
        """Keep cache ownership stable while copying execution state."""
        memo[id(self)] = self
        return self

    # generates a hash for a key
    def _hash(self, key:str) -> int:
        return hash(key) % self.table_size

    '''
    double table size then rehash old entries for the new size
    '''
    def _grow(self):
        self.table_size *= 2

        if self.parent is None:
            logging.info(f'Core cache growing to {self.table_size}')
        else:
            logging.debug(f'Cache growing to {self.table_size}')

        # swap old pointer here
        old = self._data
        self._data = []
        for i in old:
            if i[2] is not None:
                self.set(i[1], i[2], i[3], i[4])

    '''
    Finds a place for a key

    1. Direct match
    2. Find place off of direct match
    3. Grow the table all together then re-insert
    '''
    def _find(self, key:str) -> int:
        i = self._hash(key)
        for j in range(self.table_size):
            cur = (i + j) % self.table_size
            cur_key = self._data[cur][1]
            if cur_key is None or cur_key == key:
                return cur
        
        # grow and find a new place
        self._grow()
        return self._find(key)

    def _merge(self, cache:Cache) -> Cache:
        for i in cache._data:
            if i[1] is None or i[4]:
                continue
            self._set(*i[1:])
        return self

    def get_size(self) -> dict:
        with self.lock:
            size = 0
            for i in self._data:
                if i[3] is not None:
                    size += sys.getsizeof(i[3])

            return {
                'num': self.__len__(),
                'size': size
            }

    def merge(self, cache:Cache) -> Cache:
        with self.lock:
            return self._merge(cache)

    def write_back(self):
        if self.parent is None:
            return

        with self.lock:
            self.parent.merge(self)

    def _set(self, key:str, expiration:datetime | None, data:Any, dirty:bool=False):
        index = self._find(key)
        self._data[index] = (self._hash(key), key, expiration, data, dirty)

    def set(self, key:str, expiration:datetime | None, data:Any, dirty:bool=False):
        with self.lock:
            self._set(key, expiration, data, dirty=dirty)

    def get(self, key:str) -> Any:
        # lock for our data
        with self.lock:
            data = self._data[self._find(key)]
            # if data[3] is not None:
            #     logging.debug(f'Cache hit for {key}')
            # else:
            #     logging.debug(f'Cache fail for {key}')
            if data[3] is not None:
                return data[3]

        logging.debug('local miss')

        # doesn't require lock, we're accessing someone else's cache
        # their cache handles the lock
        if self.parent is not None:
            hit = self.parent.get(key)
        else:
            hit = None

        if hit is not None:
            logging.debug('Parent hit')
            self.set(key, None, hit, dirty=True)

        return hit
