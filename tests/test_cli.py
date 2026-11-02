import pytest
from typer.testing import CliRunner

import database
from cli import app


runner = CliRunner()


def invoke(*arguments: str):
    return runner.invoke(app, list(arguments))


def test_public_cli_commands_manage_students(isolated_database) -> None:
    created = invoke(
        "add",
        "--name",
        "  Ada Lovelace  ",
        "--age",
        "36",
        "--birthday",
        "1815-12-10",
        "--course",
        "  Mathematics  ",
    )
    assert created.exit_code == 0
    assert "Student 1 created." in created.output

    listed = invoke("list")
    assert listed.exit_code == 0
    assert "Ada Lovelace" in listed.output

    shown = invoke("show", "1")
    assert shown.exit_code == 0
    assert "Ada Lovelace" in shown.output

    edited = invoke("edit", "1", "--name", "  Grace Hopper  ", "--age", "37")
    assert edited.exit_code == 0
    assert "Student 1 updated." in edited.output

    student = database.get_student(1)
    assert student is not None
    assert student.name == "Grace Hopper"
    assert student.age == 37

    deleted = invoke("delete", "1", "--yes")
    assert deleted.exit_code == 0
    assert "Student 1 deleted." in deleted.output
    assert database.get_student(1) is None


@pytest.mark.parametrize(
    "arguments",
    [
        ("add", "--name", "   ", "--age", "36", "--birthday", "1815-12-10", "--course", "Math"),
        ("add", "--name", "Ada", "--age", "0", "--birthday", "1815-12-10", "--course", "Math"),
        ("add", "--name", "Ada", "--age", "131", "--birthday", "1815-12-10", "--course", "Math"),
        ("add", "--name", "Ada", "--age", "not-a-number", "--birthday", "1815-12-10", "--course", "Math"),
        ("add", "--name", "Ada", "--age", "36", "--birthday", "10-12-1815", "--course", "Math"),
        ("add", "--name", "Ada", "--age", "36", "--birthday", "2023-02-29", "--course", "Math"),
    ],
)
def test_invalid_add_input_is_readable_and_does_not_store_data(
    isolated_database, arguments: tuple[str, ...]
) -> None:
    result = invoke(*arguments)

    assert result.exit_code == 1
    assert "Error:" in result.output
    assert "Traceback" not in result.output
    assert database.get_students() == []


def test_rejected_edit_does_not_change_stored_data(isolated_database) -> None:
    created = invoke(
        "add",
        "--name",
        "Ada Lovelace",
        "--age",
        "36",
        "--birthday",
        "1815-12-10",
        "--course",
        "Mathematics",
    )
    assert created.exit_code == 0

    result = invoke("edit", "1", "--age", "0")

    assert result.exit_code == 1
    assert "Error:" in result.output
    assert "Traceback" not in result.output
    student = database.get_student(1)
    assert student is not None
    assert student.age == 36


@pytest.mark.parametrize(
    "arguments",
    [("show", "999"), ("edit", "999", "--name", "Nobody"), ("delete", "999", "--yes")],
)
def test_missing_students_return_a_readable_error(
    isolated_database, arguments: tuple[str, ...]
) -> None:
    result = invoke(*arguments)

    assert result.exit_code == 1
    assert "Error:" in result.output
    assert "Traceback" not in result.output


def test_declining_delete_keeps_the_student(isolated_database) -> None:
    created = invoke(
        "add",
        "--name",
        "Ada Lovelace",
        "--age",
        "36",
        "--birthday",
        "1815-12-10",
        "--course",
        "Mathematics",
    )
    assert created.exit_code == 0

    result = runner.invoke(app, ["delete", "1"], input="n\n")

    assert result.exit_code == 0
    assert "Cancelled." in result.output
    assert database.get_student(1) is not None
