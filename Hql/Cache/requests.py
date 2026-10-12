from __future__ import annotations
import logging
from typing import TYPE_CHECKING, Callable, Unpack

from requests import Session, Response

from .Cache import Cache

if TYPE_CHECKING:
    from requests import _types as _t

class CacheSession(Session):
    def __init__(self, cache: Cache | None = None, session: Session | None = None) -> None:
        super().__init__()
        self.cache:Cache = Cache() if cache is None else cache
        self.session = session

    def get(
        self,
        url: _t.UriType,
        params: _t.ParamsType = None,
        *,
        on_miss: Callable[[], None] | None = None,
        **kwargs: Unpack[_t.GetKwargs],
    ) -> Response:
        key = str(url) + ' ' + str(params) # + ' ' + str(kwargs)
        hit = self.cache.get(key)

        if hit is not None:
            return hit

        if on_miss is not None:
            on_miss()

        if self.session is None:
            res = super().get(url, params, **kwargs)
        else:
            res = self.session.get(url, params=params, **kwargs)
        self.cache.set(key, None, res)

        return res
