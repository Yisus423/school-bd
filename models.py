"""SQLModel tables and Pydantic validation schemas for students."""

import re
from datetime import date
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


class Student(SQLModel, table=True):
    """Student table mapped to the existing ``students`` SQLite table."""

    model_config = ConfigDict(extra="forbid")

    __tablename__ = "students"

    id: int | None = Field(default=None, primary_key=True)
    name: TrimmedName
    age: Age
    birthday: Birthday
    course: TrimmedCourse


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
