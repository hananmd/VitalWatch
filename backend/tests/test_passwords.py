from argon2 import PasswordHasher

from vitalwatch.core.passwords import hash_password, make_hasher, verify_password

_PLAIN = "correct-horse-battery-staple"


def test_hash_is_argon2id_and_hides_the_password() -> None:
    hashed = hash_password(make_hasher("test"), _PLAIN)

    assert hashed.startswith("$argon2id$")
    assert _PLAIN not in hashed
    assert verify_password(make_hasher("test"), _PLAIN, hashed)
    assert not verify_password(make_hasher("test"), "wrong-password", hashed)


def test_verify_rejects_a_value_that_is_not_a_hash() -> None:
    assert not verify_password(make_hasher("test"), _PLAIN, "not-a-hash")


def test_production_parameters_follow_the_owasp_argon2id_choice() -> None:
    hasher: PasswordHasher = make_hasher("local")
    hashed = hash_password(hasher, _PLAIN)

    assert hashed.startswith("$argon2id$v=19$m=19456,t=2,p=1$")


def test_test_hasher_stays_argon2id_with_a_smaller_memory_cost() -> None:
    hashed = hash_password(make_hasher("test"), _PLAIN)

    assert hashed.startswith("$argon2id$v=19$m=8192,t=1,p=1$")
