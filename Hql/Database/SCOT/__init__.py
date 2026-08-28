"""SCOT database adapter and its endpoint/query support layers."""

from .SCOT import SCOT
from .SCOTCatalog import Endpoint, QueryParameter, SCOT_ENDPOINTS, SCOT_TABLES

__all__ = [
    "Endpoint",
    "QueryParameter",
    "SCOT",
    "SCOT_ENDPOINTS",
    "SCOT_TABLES",
]
