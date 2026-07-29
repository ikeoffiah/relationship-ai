"""Shared markers for tests that cannot run on every database backend.

Three tests in this suite exercise things only PostgreSQL can do: pgvector
similarity search, a row-immutability trigger, and a CHECK constraint. SQLite
silently ignores the last two and rejects the first as a syntax error.

They were simply failing, and had been for long enough that "nine red, all
expected" was the normal state of the suite. That is corrosive — a suite nobody
expects to be green is a suite whose failures nobody reads, and the two real
bugs fixed alongside this had been hiding in exactly that noise. Skipping with a
stated reason keeps the signal: on Postgres they run, and on SQLite they say
why they did not.
"""

import unittest

from django.db import connection


#: Evaluated at import, not passed as a callable. `skipUnless` takes a
#: *condition*, and a function object is always truthy — passing `_is_postgres`
#: rather than `_is_postgres()` produces a decorator that never skips anything,
#: which is exactly the silent no-op this module exists to avoid.
IS_POSTGRES = connection.vendor == "postgresql"

#: For tests that need pgvector, a trigger, or a CHECK constraint.
requires_postgres = unittest.skipUnless(
    IS_POSTGRES,
    "needs PostgreSQL — SQLite cannot express this (pgvector operators, "
    "row triggers, or CHECK constraints)",
)
