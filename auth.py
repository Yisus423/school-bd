"""Passwords and session tokens on the Python standard library.

The project stores no plaintext password and adds no hashing dependency: a password
becomes a self-describing ``scrypt`` string that carries its own parameters, so a
future change of cost can be told apart from an old hash. Verification is constant
time, and a malformed or hostile stored value is rejected instead of crashing. A
session token is only ever stored as its digest, so a leaked table holds no live
session.
"""

import base64
import hashlib
import hmac
import secrets


SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1
SCRYPT_DKLEN = 32
SCRYPT_MAXMEM = 64 * 1024 * 1024
SALT_BYTES = 16
MIN_PASSWORD_LENGTH = 8
SESSION_TOKEN_BYTES = 32

_HASH_SCHEME = "scrypt"
_FIELDS = 6


def _encode(raw: bytes) -> str:
    """Encode bytes as unpadded URL-safe base64, so ``$`` stays a separator."""
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _decode(value: str) -> bytes:
    """Decode the output of ``_encode``, rejecting anything malformed."""
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def hash_password(password: str) -> str:
    """Return a fresh salted scrypt hash for ``password``.

    Raises ``ValueError`` when the password is shorter than the documented minimum.
    """
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(
            f"password must be at least {MIN_PASSWORD_LENGTH} characters long"
        )
    salt = secrets.token_bytes(SALT_BYTES)
    digest = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=SCRYPT_N,
        r=SCRYPT_R,
        p=SCRYPT_P,
        dklen=SCRYPT_DKLEN,
        maxmem=SCRYPT_MAXMEM,
    )
    return "$".join(
        (
            _HASH_SCHEME,
            str(SCRYPT_N),
            str(SCRYPT_R),
            str(SCRYPT_P),
            _encode(salt),
            _encode(digest),
        )
    )


def new_session_token() -> str:
    """Return a fresh unguessable token for one session cookie."""
    return secrets.token_urlsafe(SESSION_TOKEN_BYTES)


def hash_session_token(token: str) -> str:
    """Return the digest this project stores in place of a session token."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _parse(stored: str) -> tuple[int, int, int, bytes, bytes] | None:
    """Split a stored hash, refusing unknown schemes and absurd work factors."""
    parts = stored.split("$")
    if len(parts) != _FIELDS or parts[0] != _HASH_SCHEME:
        return None
    try:
        n, r, p = (int(part) for part in parts[1:4])
        salt = _decode(parts[4])
        digest = _decode(parts[5])
    except ValueError:
        return None
    if not 0 < n <= 2**20 or not 0 < r <= 32 or not 0 < p <= 16:
        return None
    if not digest or not salt:
        return None
    return n, r, p, salt, digest


def verify_password(password: str, stored: str) -> bool:
    """Report whether ``password`` matches a stored hash, without leaking timing."""
    parsed = _parse(stored)
    if parsed is None:
        return False
    n, r, p, salt, digest = parsed
    try:
        candidate = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=n,
            r=r,
            p=p,
            dklen=len(digest),
            maxmem=SCRYPT_MAXMEM,
        )
    except ValueError:
        return False
    return hmac.compare_digest(candidate, digest)
