"""Argon2id password hashing.

The hash string is the only thing that may be stored. Callers must not log the
plain password or put it in an error response.
"""

import secrets

from argon2 import PasswordHasher, Type
from argon2.exceptions import Argon2Error, InvalidHashError

# OWASP password-storage cheat sheet: Argon2id, 19 MiB, 2 iterations, parallelism 1.
_PRODUCTION = {"time_cost": 2, "memory_cost": 19 * 1024, "parallelism": 1}
# Same algorithm, less memory, so the test suite is not dominated by hashing.
_TEST = {"time_cost": 1, "memory_cost": 8 * 1024, "parallelism": 1}


def make_hasher(environment: str) -> PasswordHasher:
    params = _TEST if environment == "test" else _PRODUCTION
    return PasswordHasher(**params, type=Type.ID)


def hash_password(hasher: PasswordHasher, password: str) -> str:
    return hasher.hash(password)


def verify_password(hasher: PasswordHasher, password: str, password_hash: str) -> bool:
    try:
        return hasher.verify(password_hash, password)
    except (Argon2Error, InvalidHashError):
        return False


_dummy_hashes: dict[int, str] = {}


def dummy_hash(hasher: PasswordHasher) -> str:
    """A throwaway hash so a missing user takes about as long to reject as a wrong password."""
    cached = _dummy_hashes.get(id(hasher))
    if cached is None:
        cached = hasher.hash(secrets.token_urlsafe(32))
        _dummy_hashes[id(hasher)] = cached
    return cached
