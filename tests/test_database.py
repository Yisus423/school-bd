from datetime import date

from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import URL

import database


def test_crud_helpers_persist_sqlmodel_students(isolated_database) -> None:
    created = database.add_student(
        "  Ada Lovelace  ",
        36,
        "1815-12-10",
        "  Mathematics  ",
    )

    assert created.id is not None
    assert created.name == "Ada Lovelace"
    assert created.course == "Mathematics"

    loaded = database.get_student(created.id)
    assert loaded is not None
    assert loaded.id == created.id
    assert loaded.age == 36
    assert loaded.birthday == date(1815, 12, 10)
    assert loaded.course == "Mathematics"

    students = database.get_students()
    assert [(student.id, student.name) for student in students] == [
        (created.id, "Ada Lovelace")
    ]

    updated = database.edit_student(
        created.id,
        name="  Grace Hopper  ",
        age=37,
    )
    assert updated is not None
    assert updated.name == "Grace Hopper"
    assert updated.age == 37

    persisted = database.get_student(created.id)
    assert persisted is not None
    assert persisted.name == "Grace Hopper"
    assert persisted.age == 37

    assert database.delete_student(created.id) is True
    assert database.get_student(created.id) is None
    assert database.delete_student(created.id) is False


def test_sqlmodel_table_keeps_the_existing_student_columns(isolated_database) -> None:
    inspector = inspect(isolated_database)

    assert inspector.has_table("students") is True
    assert {column["name"] for column in inspector.get_columns("students")} == {
        "id",
        "name",
        "age",
        "birthday",
        "course",
    }


def test_legacy_students_table_remains_readable_and_writable(
    tmp_path, monkeypatch
) -> None:
    database_path = tmp_path / "legacy.sqlite3"
    legacy_engine = create_engine(
        URL.create("sqlite", database=str(database_path)),
        connect_args={"check_same_thread": False},
    )
    with legacy_engine.begin() as connection:
        connection.exec_driver_sql(
            """
            CREATE TABLE students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                age INTEGER NOT NULL,
                birthday TEXT NOT NULL,
                course TEXT NOT NULL
            )
            """
        )
        connection.exec_driver_sql(
            """
            INSERT INTO students (id, name, age, birthday, course)
            VALUES (1, 'Legacy Student', 20, '2005-04-03', 'Legacy Course')
            """
        )

    monkeypatch.setattr(database, "engine", legacy_engine)
    database.initialize_database()

    student = database.get_student(1)
    assert student is not None
    assert student.name == "Legacy Student"
    assert student.birthday == date(2005, 4, 3)

    updated = database.edit_student(1, course="  Updated Course  ")
    assert updated is not None
    assert updated.course == "Updated Course"

    legacy_engine.dispose()
