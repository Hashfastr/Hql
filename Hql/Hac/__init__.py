from __future__ import annotations
from Hql.Exceptions import HacExceptions as hace
from typing import TYPE_CHECKING, Optional, Union
from datetime import timedelta

if TYPE_CHECKING:
    from datetime import datetime

class Hac():
    '''
    asm is the output of the parser
    src is a string identifier of the origin of the HaC, e.g. a filename
    default_schedule is if there is an undefined schedule, safe defaults to hourly
    '''
    def __init__(self, asm:dict, src:str, default_schedule:str='0 * * * *', username:str='Username', start:Optional[datetime]=None, end:Optional[datetime]=None) -> None:
        from datetime import datetime
        import uuid
        self.id = str(uuid.uuid4())
        self.schedule:str = default_schedule
        # How far back a run looks, None for the schedule's interval
        self.lookback:Optional[timedelta] = None
        self.set_query_now(datetime.now())

        if not asm:
            asm = {
                'title': 'my detection',
                'author': 'Unknown',
                'id': self.id,
                'status': 'testing',
                'level': 'medium',
                'schedule': self.schedule,
                'description': 'Parasaurolophus is a great dinosaur',
                'tags': ['tag'],
                'triage': 'drink celsius',
                'falsepositives': ['certainly'],
                'authornotes': '',
                'references': ['https://hql.dev'],
                'changelog': [
                    f'{datetime.now().strftime("%Y-%m-%d")} {username}: Init detection'
                ]
            }

        self.asm = asm
        self.src = src

        # Required tags from a HaC definition
        self.required = [
            'title',
            'author',
            'id',
            'status',
            'schedule',
            'description',
        ]

        self.order = [
            'title',
            'author',
            'id',
            'status',
            'level',
            'schedule',
            'description',
            'tags',
            'triage',
            'falsepositives',
            'authornotes',
            'references',
            'changelog'
        ]

        self.validate()
        self.reorder_keys()

    def render(self, target:str='md'):
        from .Doc import HacDoc

        hd = HacDoc(self)
        
        if target in ('md', 'markdown'):
            return hd.markdown()

        if target == 'json':
            return hd.json()

        if target == 'decompile':
            return hd.decompile()

        if target == 'html':
            return hd.html()

        raise hace.HacException(f'Unknown HaC render type {target}')

    def set_query_now(self, query_now:datetime):
        self.end = query_now
        self.start = query_now - self.get_delta()

    def get_delta(self) -> timedelta:
        from Hql.Hac.Engine import Schedule
        if self.lookback is not None:
            return self.lookback
        return Schedule(self.schedule).delta()

    def set_lookback(self, lookback:Optional[timedelta]) -> None:
        '''Look this far back from the query time, None goes back to the schedule's interval.'''
        if lookback is not None and lookback <= timedelta(0):
            raise hace.HacException(f'Lookback must be positive, got {lookback}')
        self.lookback = lookback
        self.set_query_now(self.end)

    def get_timerange(self) -> tuple[datetime, datetime]:
        return self.start, self.end
    
    def get(self, name:str) -> Union[str, list[str]]:
        if name == 'src':
            return self.src
        return self.asm.get(name, '')

    def reorder_keys(self):
        new = dict()

        for i in self.order:
            if i not in self.asm:
                continue
            new[i] = self.asm.pop(i)

        for i in self.asm:
            new[i] = self.asm[i]

        self.asm = new

    def validate(self):
        for i in self.required:
            if i not in self.asm:
                if i == 'schedule':
                    self.asm['schedule'] = self.schedule

                elif i == 'author':
                    self.asm['author'] = 'Unknown'

                elif i == 'id':
                    self.asm['id'] = self.id

                # Optional in Sigma
                elif i == 'description' and self.src == 'sigma':
                    self.asm['description'] = ''

                else:
                    raise hace.HacException(f'Missing required field {i} in {self.src}')

        self.id = self.asm['id']
        self.schedule = self.asm['schedule']
