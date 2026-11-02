"""SQLite persistence for students using SQLModel sessions."""

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy.engine import URL
from sqlmodel import Session, SQLModel, create_engine, select

from models import Student, StudentUpdate


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
