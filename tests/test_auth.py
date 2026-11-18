import pytest

import auth


def test_a_password_verifies_only_against_its_own_hash() -> None:
    stored = auth.hash_password("una-clave-larga")

    assert stored.startswith("scrypt$")
    assert "una-clave-larga" not in stored
    assert auth.verify_password("una-clave-larga", stored) is True
    assert auth.verify_password("una-clave-larg", stored) is False
    assert auth.verify_password("", stored) is False


def test_the_same_password_never_produces_the_same_hash_twice() -> None:
    assert auth.hash_password("una-clave-larga") != auth.hash_password("una-clave-larga")


@pytest.mark.parametrize(
    "stored",
    [
        "",
        "garbage",
        "scrypt$16384$8$1$aa",
        "bcrypt$16384$8$1$aa$bb",
        "scrypt$0$8$1$aa$bb",
        "scrypt$99999999$8$1$aa$bb",
        "scrypt$16384$9999$1$aa$bb",
        "scrypt$16384$8$1$aa$",
    ],
)
def test_a_damaged_stored_hash_never_verifies(stored: str) -> None:
    assert auth.verify_password("una-clave-larga", stored) is False


def test_a_password_shorter_than_the_minimum_is_refused() -> None:
    with pytest.raises(ValueError, match="at least 8 characters"):
        auth.hash_password("corta12")
