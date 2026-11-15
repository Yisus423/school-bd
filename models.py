"""SQLModel tables and Pydantic validation schemas for students and accounts."""

import re
from datetime import date
from enum import StrEnum
from typing import Annotated

from pydantic import BeforeValidator, ConfigDict, StringConstraints, model_validator
from sqlmodel import Field, SQLModel


def _parse_birthday(value: object) -> object:
    """Require the public YYYY-MM-DD representation and a real calendar date."""
    if isinstance(value, date):
        return value
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError("birthday must use the YYYY-MM-DD format")
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise ValueError("birthday must be a valid calendar date") from error


TrimmedName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
TrimmedCourse = Annotated[str, StringConstraints(strip_whitespace=True)]
Age = Annotated[int, Field(ge=1, le=130)]
Birthday = Annotated[date, BeforeValidator(_parse_birthday)]


class Role(StrEnum):
    """What an account is allowed to do."""

    student = "student"
    teacher = "teacher"
    admin = "admin"


_USERNAME = re.compile(r"[a-z0-9][a-z0-9._-]{2,31}")


def normalize_username(value: object) -> str:
    """Normalize a username and accept only the documented character set.

    Accounts and lookups share this function, so ``Ana.Perez`` and ``ana.perez`` are
    the same account and a login cannot miss it by letter case.
    """
    if not isinstance(value, str):
        raise ValueError("username must be text")
    username = value.strip().lower()
    if not _USERNAME.fullmatch(username):
        raise ValueError(
            "username must be 3 to 32 characters long and use only letters, "
            "digits, dots, dashes or underscores"
        )
    return username


Username = Annotated[str, BeforeValidator(normalize_username)]


class Student(SQLModel, table=True):
    """Student table mapped to the existing ``students`` SQLite table."""

    model_config = ConfigDict(extra="forbid")

    __tablename__ = "students"

    id: int | None = Field(default=None, primary_key=True)
    name: TrimmedName
    age: Age
    birthday: Birthday
    course: TrimmedCourse


class User(SQLModel, table=True):
    """Account that can sign in to the web UI.

    The password itself is never stored: ``password_hash`` holds the self-describing
    output of ``auth.hash_password``. A ``student`` account is linked to the student
    record it owns; a ``teacher`` or ``admin`` account has no record of its own.
    """

    model_config = ConfigDict(extra="forbid")

    __tablename__ = "users"

    id: int | None = Field(default=None, primary_key=True)
    username: Username = Field(unique=True, index=True)
    password_hash: str
    role: Role
    student_id: int | None = Field(default=None, foreign_key="students.id")

    @model_validator(mode="after")
    def keep_student_links_student_only(self) -> "User":
        if self.role is Role.student and self.student_id is None:
            raise ValueError("a student account must be linked to a student record")
        if self.role is not Role.student and self.student_id is not None:
            raise ValueError(
                "only a student account can be linked to a student record"
            )
        return self


class StudentUpdate(SQLModel):
    """Validated partial update for a student."""

    model_config = ConfigDict(extra="forbid")

    name: TrimmedName | None = None
    age: Age | None = None
    birthday: Birthday | None = None
    course: TrimmedCourse | None = None

    @model_validator(mode="after")
    def reject_explicit_null_values(self) -> "StudentUpdate":
        null_fields = [
            field_name
            for field_name in self.model_fields_set
            if getattr(self, field_name) is None
        ]
        if null_fields:
            fields = ", ".join(sorted(null_fields))
            raise ValueError(f"updated fields cannot be null: {fields}")
        return self
