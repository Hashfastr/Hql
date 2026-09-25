"""SCOT database adapter and its endpoint/query support layers."""

'''
This was AI generated and sure it's right but god I hate it
'''

from .SCOT import SCOT
from .SCOTCatalog import (
    Endpoint,
    QueryParameter,
    SCOT_ENDPOINTS,
    SCOT_RELATIONSHIPS,
    SCOT_TABLES,
)

__all__ = [
    "Endpoint",
    "QueryParameter",
    "SCOT",
    "SCOT_ENDPOINTS",
    "SCOT_RELATIONSHIPS",
    "SCOT_TABLES",
]
