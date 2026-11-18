"""SQLite persistence for students, accounts and sessions."""

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy.engine import URL
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, SQLModel, create_engine, select

from auth import hash_password, hash_session_token, new_session_token, verify_password
from models import (
    LoginSession,
    Role,
    Student,
    StudentUpdate,
    User,
    normalize_username,
)


SESSION_TTL = timedelta(hours=8)


DB_PATH = Path(__file__).resolve().parent / "db.sqlite3"
engine = create_engine(
    URL.create("sqlite", database=str(DB_PATH)),
    connect_args={"check_same_thread": False},
)


def initialize_database() -> None:
    """Create the SQLModel tables when they do not already exist."""
    SQLModel.metadata.create_all(engine)


@contextmanager
def session_scope() -> Iterator[Session]:
    """Provide a transactional SQLModel session."""
    initialize_database()
    session = Session(engine, expire_on_commit=False)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def add_student(name: str, age: int, birthday: str, course: str) -> Student:
    """Validate and persist one student."""
    student = Student.model_validate(
        {"name": name, "age": age, "birthday": birthday, "course": course}
    )
    with session_scope() as session:
        session.add(student)
        session.flush()
        session.refresh(student)
    return student


def get_students() -> list[Student]:
    """Return every student ordered by its identifier."""
    with session_scope() as session:
        return list(session.exec(select(Student).order_by(Student.id)).all())


def get_student(student_id: int) -> Student | None:
    """Return one student by identifier, if it exists."""
    with session_scope() as session:
        return session.get(Student, student_id)


def edit_student(student_id: int, **fields: object) -> Student | None:
    """Validate and apply a partial update to one student."""
    if not fields:
        raise ValueError("You must provide at least one field to update")
    update = StudentUpdate(**fields)

    with session_scope() as session:
        student = session.get(Student, student_id)
        if student is None:
            return None
        for field_name, value in update.model_dump(exclude_unset=True).items():
            setattr(student, field_name, value)
        session.add(student)
        session.flush()
        session.refresh(student)
    return student


def delete_student(student_id: int) -> bool:
    """Delete one student and report whether it existed."""
    with session_scope() as session:
        student = session.get(Student, student_id)
        if student is None:
            return False
        session.delete(student)
    return True


def _find_user(session: Session, username: str) -> User | None:
    """Find one account by its normalized username."""
    try:
        normalized = normalize_username(username)
    except ValueError:
        return None
    return session.exec(select(User).where(User.username == normalized)).first()


_absent_user_hash: str | None = None


def _verify_against_absent_user(password: str) -> None:
    """Spend the same work on an unknown username as on a wrong password.

    Without this, a missing account would answer faster than an existing one and the
    response time itself would tell a caller which usernames exist.
    """
    global _absent_user_hash
    if _absent_user_hash is None:
        _absent_user_hash = hash_password("a password no account owns")
    verify_password(password, _absent_user_hash)


def add_user(
    username: str,
    password: str,
    role: Role | str,
    student_id: int | None = None,
) -> User:
    """Hash the password, validate the account and persist it."""
    user = User.model_validate(
        {
            "username": username,
            "password_hash": hash_password(password),
            "role": role,
            "student_id": student_id,
        }
    )
    try:
        with session_scope() as session:
            session.add(user)
            session.flush()
            session.refresh(user)
    except IntegrityError as error:
        raise ValueError(f"username '{user.username}' is already taken") from error
    return user


def get_user_by_username(username: str) -> User | None:
    """Return one account by username, if it exists."""
    with session_scope() as session:
        return _find_user(session, username)


def list_users() -> list[User]:
    """Return every account ordered by its identifier."""
    with session_scope() as session:
        return list(session.exec(select(User).order_by(User.id)).all())


def authenticate(username: str, password: str) -> User | None:
    """Return the account when the password matches it, and nothing otherwise."""
    user = get_user_by_username(username)
    if user is None:
        _verify_against_absent_user(password)
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def set_user_password(username: str, password: str) -> bool:
    """Replace one account's password and report whether it existed."""
    new_hash = hash_password(password)
    with session_scope() as session:
        user = _find_user(session, username)
        if user is None:
            return False
        user.password_hash = new_hash
        session.add(user)
    return True


def delete_user(username: str) -> bool:
    """Delete one account and report whether it existed."""
    with session_scope() as session:
        user = _find_user(session, username)
        if user is None:
            return False
        session.delete(user)
    return True


def _utc_now() -> datetime:
    """Aware UTC: the session deadline column rejects a datetime without a zone."""
    return datetime.now(timezone.utc)


def _find_session(session: Session, token: str) -> LoginSession | None:
    """Find one session by the digest of its cookie token."""
    digest = hash_session_token(token)
    return session.exec(
        select(LoginSession).where(LoginSession.token_hash == digest)
    ).first()


def create_session(user_id: int, ttl: timedelta = SESSION_TTL) -> str:
    """Open a session for one account and return the token its cookie carries."""
    token = new_session_token()
    login = LoginSession.model_validate(
        {
            "token_hash": hash_session_token(token),
            "user_id": user_id,
            "expires_at": _utc_now() + ttl,
        }
    )
    with session_scope() as session:
        session.add(login)
    return token


def session_user(token: str) -> User | None:
    """Return the account a live session belongs to, and nothing otherwise.

    An expired session is deleted on the spot, and a session whose account is gone
    resolves to nothing, so a removed account cannot keep using an open browser.
    """
    if not token:
        return None
    with session_scope() as session:
        login = _find_session(session, token)
        if login is None:
            return None
        if login.expires_at <= _utc_now():
            session.delete(login)
            return None
        return session.get(User, login.user_id)


def delete_session(token: str) -> bool:
    """Close one session and report whether it was still open."""
    if not token:
        return False
    with session_scope() as session:
        login = _find_session(session, token)
        if login is None:
            return False
        session.delete(login)
    return True


def purge_expired_sessions() -> int:
    """Delete every session past its deadline and report how many were removed."""
    with session_scope() as session:
        expired = list(
            session.exec(
                select(LoginSession).where(LoginSession.expires_at <= _utc_now())
            ).all()
        )
        for login in expired:
            session.delete(login)
    return len(expired)
