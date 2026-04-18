"""Exceptions for the stare query DSL."""
from __future__ import annotations


class DSLError(Exception):
    """Base class for all DSL errors."""


class DSLSyntaxError(DSLError):
    """Raised when the input cannot be parsed by the grammar."""


class DSLValidationError(DSLError):
    """Raised when a field name or operator fails semantic validation."""
