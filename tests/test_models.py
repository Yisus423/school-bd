from datetime import date

import pytest
from pydantic import ValidationError

from models import Student, StudentUpdate


def make_student(**overrides: object) -> Student:
    values = {
        "name": "Ada Lovelace",
        "age": 36,
        "birthday": "1815-12-10",
        "course": "Mathematics",
    }
    values.update(overrides)
    return Student.model_validate(values)


def test_student_normalizes_name_and_course() -> None:
    student = make_student(
        name="  Ada Lovelace  ",
        course="  Mathematics  ",
    )

    assert student.name == "Ada Lovelace"
    assert student.course == "Mathematics"
    assert student.birthday == date(1815, 12, 10)


@pytest.mark.parametrize("name", ["", "   ", "\t\n"])
def test_student_rejects_a_blank_name(name: str) -> None:
    with pytest.raises(ValidationError):
        make_student(name=name)


@pytest.mark.parametrize("age", [1, 130])
def test_student_accepts_age_boundaries(age: int) -> None:
    student = make_student(age=age)

    assert student.age == age


@pytest.mark.parametrize("age", [0, 131])
def test_student_rejects_ages_outside_the_allowed_range(age: int) -> None:
    with pytest.raises(ValidationError):
        make_student(age=age)


@pytest.mark.parametrize(
    "birthday",
    ["10-12-1815", "1815/12/10", "1815-12-32", "2023-02-29"],
)
def test_student_rejects_invalid_birthdays(birthday: str) -> None:
    with pytest.raises(ValidationError):
        make_student(birthday=birthday)


def test_student_update_validates_only_supplied_fields() -> None:
    update = StudentUpdate(name="  Grace Hopper  ", age=37)

    assert update.model_dump(exclude_unset=True) == {
        "name": "Grace Hopper",
        "age": 37,
    }


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("name", "   "),
        ("age", 0),
        ("age", 131),
        ("birthday", "1815/12/10"),
    ],
)
def test_student_update_rejects_invalid_values(field: str, value: object) -> None:
    with pytest.raises(ValidationError):
        StudentUpdate(**{field: value})
