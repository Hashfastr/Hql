from __future__ import annotations
import logging
from typing import TYPE_CHECKING, Unpack

from requests import Session, Response

from .Cache import Cache

if TYPE_CHECKING:
    from requests import _types as _t

class CacheSession(Session):
    def __init__(self, cache: Cache | None = None) -> None:
        super().__init__()
        self.cache:Cache = Cache() if cache is None else cache

    def get(self, url: _t.UriType, params: _t.ParamsType = None, **kwargs: Unpack[_t.GetKwargs]) -> Response:
        hit = self.cache.get(str(url))

        if hit is not None:
            return hit

        res = super().get(url, params, **kwargs)
        self.cache.set(str(url), None, res)

        return res
