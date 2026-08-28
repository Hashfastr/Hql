from __future__ import annotations
from .BranchDescriptor import BranchDescriptor
from .InstructionSet import InstructionSet
from .Compiler import Compiler
from .Lucene import LuceneCompiler
from .QueryDSL import QueryDSLCompiler
from .Splunk import SPLCompiler
from .Hql import HqlCompiler
from .Sql import SqlCompiler
from .SCOT import SCOTCompiler

from Hql.Exceptions import HqlExceptions as hqle

target_registry = {}

def register_target(name:str):
    def decorator(cls):
        if not issubclass(cls, Compiler):
            raise hqle.CompilerException(f'Attempting to register non-target class {name} as a target')

        target_registry[name] = cls
        return cls
    return decorator

def get_target(name:str):
    if name in target_registry:
        return target_registry[name]
    else:
        raise hqle.CompilerException(f"Unknown target type {name}")

def compile_target(target:str):
    ...
