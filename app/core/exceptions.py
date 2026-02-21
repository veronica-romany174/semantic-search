"""
app/core/exceptions.py

Custom exception hierarchy for the application.

Raising typed exceptions from services lets controllers catch specific
cases and return the correct HTTP status code without leaking internals.
"""


class AppBaseException(Exception):
    """Root exception — catch-all for any application-level error."""
