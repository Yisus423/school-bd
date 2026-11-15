import pytest
from typer.testing import CliRunner

import database
from cli import app
from models import Role


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


def test_users_add_creates_an_account_that_can_sign_in(isolated_database) -> None:
    result = invoke(
        "users",
        "add",
        "--username",
        "  Ada.Lovelace  ",
        "--role",
        "teacher",
        "--password",
        "una-clave-larga",
    )

    assert result.exit_code == 0
    assert "Account ada.lovelace created." in result.output
    account = database.authenticate("ada.lovelace", "una-clave-larga")
    assert account is not None
    assert account.role is Role.teacher
    assert account.student_id is None
    assert database.authenticate("ada.lovelace", "otra-clave-larga") is None
    assert database.authenticate("nadie", "una-clave-larga") is None
    assert "una-clave-larga" not in account.password_hash


def test_the_password_is_asked_for_twice_when_the_option_is_omitted(
    isolated_database,
) -> None:
    result = runner.invoke(
        app,
        ["users", "add", "--username", "ada", "--role", "admin"],
        input="una-clave-larga\nuna-clave-larga\n",
    )

    assert result.exit_code == 0
    assert database.authenticate("ada", "una-clave-larga") is not None


def test_a_duplicate_username_is_refused_regardless_of_case(isolated_database) -> None:
    first = invoke(
        "users", "add", "--username", "ada", "--role", "teacher", "-p", "una-clave-larga"
    )
    assert first.exit_code == 0

    second = invoke(
        "users", "add", "--username", "ADA", "--role", "admin", "-p", "otra-clave-larga"
    )

    assert second.exit_code == 1
    assert "Error:" in second.output
    assert "already taken" in second.output
    assert "Traceback" not in second.output
    assert [account.username for account in database.list_users()] == ["ada"]
    assert database.authenticate("ada", "una-clave-larga") is not None


@pytest.mark.parametrize("role", ["student", "teacher", "admin"])
def test_every_role_can_be_created(isolated_database, role: str) -> None:
    student_id = None
    if role == "student":
        student_id = str(_create_student())

    arguments = [
        "users", "add", "--username", "ada", "--role", role, "-p", "una-clave-larga"
    ]
    if student_id is not None:
        arguments += ["--student-id", student_id]
    result = invoke(*arguments)

    assert result.exit_code == 0
    account = database.get_user_by_username("ada")
    assert account is not None
    assert account.role is Role(role)
    assert account.student_id == (int(student_id) if student_id else None)


def test_a_student_account_must_name_its_student_record(isolated_database) -> None:
    result = invoke(
        "users", "add", "--username", "ada", "--role", "student", "-p", "una-clave-larga"
    )

    assert result.exit_code == 1
    assert "Error:" in result.output
    assert "must be linked to a student record" in result.output
    assert "Traceback" not in result.output
    assert database.list_users() == []


def test_only_a_student_account_may_name_a_student_record(isolated_database) -> None:
    student_id = _create_student()

    result = invoke(
        "users",
        "add",
        "--username",
        "ada",
        "--role",
        "teacher",
        "--student-id",
        str(student_id),
        "-p",
        "una-clave-larga",
    )

    assert result.exit_code == 1
    assert "only a student account" in result.output
    assert "Traceback" not in result.output
    assert database.list_users() == []


def test_a_short_password_is_refused_and_stores_nothing(isolated_database) -> None:
    result = invoke(
        "users", "add", "--username", "ada", "--role", "admin", "-p", "corta12"
    )

    assert result.exit_code == 1
    assert "at least 8 characters" in result.output
    assert "Traceback" not in result.output
    assert database.list_users() == []


def test_an_unknown_role_is_refused(isolated_database) -> None:
    result = invoke(
        "users", "add", "--username", "ada", "--role", "principal", "-p", "una-clave-larga"
    )

    assert result.exit_code == 1
    assert "Error:" in result.output
    assert "'principal' is not one of" in result.output
    assert database.list_users() == []


def test_a_readable_username_is_required(isolated_database) -> None:
    result = invoke("users", "add", "--username", "a b", "--role", "admin", "-p", "una-clave-larga")

    assert result.exit_code == 1
    assert "Error:" in result.output
    assert "3 to 32 characters" in result.output
    assert database.list_users() == []


def test_users_passwd_replaces_the_password(isolated_database) -> None:
    created = invoke(
        "users", "add", "--username", "ada", "--role", "admin", "-p", "una-clave-larga"
    )
    assert created.exit_code == 0

    changed = invoke("users", "passwd", "--username", "ada", "-p", "otra-clave-larga")

    assert changed.exit_code == 0
    assert "Password updated for ada." in changed.output
    assert database.authenticate("ada", "una-clave-larga") is None
    assert database.authenticate("ada", "otra-clave-larga") is not None


def test_users_passwd_on_a_missing_account_changes_nothing(isolated_database) -> None:
    result = invoke("users", "passwd", "--username", "nadie", "-p", "otra-clave-larga")

    assert result.exit_code == 1
    assert "no account with username 'nadie'" in result.output
    assert database.list_users() == []


def test_users_list_shows_every_account(isolated_database) -> None:
    empty = invoke("users", "list")
    assert empty.exit_code == 0
    assert "No accounts found." in empty.output

    student_id = _create_student()
    invoke("users", "add", "--username", "ada", "--role", "student", "--student-id", str(student_id), "-p", "una-clave-larga")
    invoke("users", "add", "--username", "grace", "--role", "admin", "-p", "una-clave-larga")

    listed = invoke("users", "list")

    assert listed.exit_code == 0
    assert "ada" in listed.output and "student" in listed.output
    assert "grace" in listed.output and "admin" in listed.output


def test_users_remove_deletes_the_account_and_keeps_the_student(isolated_database) -> None:
    student_id = _create_student()
    invoke("users", "add", "--username", "ada", "--role", "student", "--student-id", str(student_id), "-p", "una-clave-larga")

    result = invoke("users", "remove", "--username", "ADA", "--yes")

    assert result.exit_code == 0
    assert "Account ADA removed." in result.output
    assert database.list_users() == []
    assert database.get_student(student_id) is not None


def test_declining_remove_keeps_the_account(isolated_database) -> None:
    invoke("users", "add", "--username", "ada", "--role", "admin", "-p", "una-clave-larga")

    result = runner.invoke(app, ["users", "remove", "--username", "ada"], input="n\n")

    assert result.exit_code == 0
    assert "Cancelled." in result.output
    assert database.get_user_by_username("ada") is not None


def test_users_remove_on_a_missing_account_changes_nothing(isolated_database) -> None:
    result = invoke("users", "remove", "--username", "nadie", "--yes")

    assert result.exit_code == 1
    assert "no account with username 'nadie'" in result.output
    assert database.list_users() == []


def _create_student() -> int:
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
    students = database.get_students()
    return students[-1].id
