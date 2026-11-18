"""Student and account CLI over database.py (Typer + Rich).

This module only translates command-line arguments, delegates persistence to
``database.py``, and renders results. Validation belongs to the Pydantic and
SQLModel schemas in ``models.py``. Passwords are only ever hashed: ``--password``
exists for scripts and tests, and every command prompts for it hidden when the
option is omitted.
"""

from typing import Annotated

import typer
from pydantic import ValidationError
from rich.box import ROUNDED
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from typer._click.exceptions import UsageError
from typer.core import TyperGroup

import database as db
from models import Role, Student


class ErrorAwareGroup(TyperGroup):
    """Render Typer usage errors with the CLI's readable error convention."""

    @staticmethod
    def _exit_with_error(error: UsageError) -> None:
        typer.echo(
            typer.style("Error: ", fg="red", bold=True) + error.format_message()
        )
        raise typer.Exit(code=1) from None

    def make_context(self, info_name, args, parent=None, **extra):
        try:
            return super().make_context(info_name, args, parent=parent, **extra)
        except UsageError as error:
            self._exit_with_error(error)

    def invoke(self, ctx):
        try:
            return super().invoke(ctx)
        except UsageError as error:
            self._exit_with_error(error)


app = typer.Typer(
    help="Students and accounts over SQLite.",
    no_args_is_help=True,
    cls=ErrorAwareGroup,
)
users_app = typer.Typer(
    help="Accounts that can sign in to the web UI.",
    no_args_is_help=True,
    cls=ErrorAwareGroup,
)
app.add_typer(users_app, name="users")
console = Console()


def fail(message: str) -> None:
    """Print a readable error and stop with exit code 1."""
    console.print(f"[bold red]Error:[/] {message}")
    raise typer.Exit(code=1)


def report_validation_error(error: ValidationError) -> None:
    """Render Pydantic's validation details without a traceback."""
    details = []
    for item in error.errors():
        message = item["msg"].removeprefix("Value error, ")
        location = ".".join(str(part) for part in item["loc"])
        details.append(f"{location}: {message}" if location else message)
    fail("invalid input: " + "; ".join(details))


def render_table(students: list[Student]) -> None:
    if not students:
        console.print("[yellow]No students found.[/]")
        return

    table = Table(title="Students", box=ROUNDED, header_style="bold cyan")
    for column in ("id", "name", "age", "birthday", "course"):
        table.add_column(
            column.capitalize(),
            justify="right" if column in {"id", "age"} else "left",
        )
    for student in students:
        table.add_row(
            str(student.id),
            student.name,
            str(student.age),
            student.birthday.isoformat(),
            student.course,
        )
    console.print(table)


@app.command("list")
def list_students() -> None:
    """List every student."""
    render_table(db.get_students())


@app.command("add")
def add_student(
    name: Annotated[str, typer.Option("--name", "-n", prompt=True, help="Full name")],
    age: Annotated[int, typer.Option("--age", "-a", prompt=True, help="Age in years")],
    birthday: Annotated[
        str, typer.Option("--birthday", "-b", prompt=True, help="Birthday as YYYY-MM-DD")
    ],
    course: Annotated[str, typer.Option("--course", "-c", prompt=True, help="Course")],
) -> None:
    """Create a new student."""
    try:
        student = db.add_student(name, age, birthday, course)
    except ValidationError as error:
        report_validation_error(error)
    console.print(f"[bold green]Student {student.id} created.[/]")


@app.command("show")
def show_student(
    student_id: Annotated[int, typer.Argument(help="Student ID")],
) -> None:
    """Show a single student."""
    student = db.get_student(student_id)
    if student is None:
        fail(f"no student with id {student_id}")

    body = "\n".join(
        (
            f"{'id':<10}{student.id}",
            f"{'name':<10}{student.name}",
            f"{'age':<10}{student.age}",
            f"{'birthday':<10}{student.birthday.isoformat()}",
            f"{'course':<10}{student.course}",
        )
    )
    console.print(Panel(body, title=f"Student {student_id}", border_style="cyan"))


@app.command("edit")
def edit_student(
    student_id: Annotated[int, typer.Argument(help="Student ID")],
    name: Annotated[str | None, typer.Option("--name", "-n")] = None,
    age: Annotated[int | None, typer.Option("--age", "-a")] = None,
    birthday: Annotated[str | None, typer.Option("--birthday", "-b")] = None,
    course: Annotated[str | None, typer.Option("--course", "-c")] = None,
) -> None:
    """Update one or more fields of a student."""
    fields = {}
    if name is not None:
        fields["name"] = name
    if age is not None:
        fields["age"] = age
    if birthday is not None:
        fields["birthday"] = birthday
    if course is not None:
        fields["course"] = course

    if not fields:
        fail("you did not pass any field; use --name, --age, --birthday or --course")

    try:
        student = db.edit_student(student_id, **fields)
    except ValidationError as error:
        report_validation_error(error)
    if student is None:
        fail(f"no student with id {student_id}")
    console.print(f"[bold green]Student {student_id} updated.[/]")


@app.command("delete")
def delete_student(
    student_id: Annotated[int, typer.Argument(help="Student ID")],
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip the confirmation")] = False,
) -> None:
    """Delete a student."""
    student = db.get_student(student_id)
    if student is None:
        fail(f"no student with id {student_id}")
    if not yes and not typer.confirm(f"Delete student {student_id}?", default=False):
        console.print("[yellow]Cancelled.[/]")
        raise typer.Exit()

    if not db.delete_student(student_id):
        fail(f"no student with id {student_id}")
    console.print(f"[bold green]Student {student_id} deleted.[/]")


def ask_password(password: str | None) -> str:
    """Return the given password, or ask for it twice without echoing it."""
    if password is not None:
        return password
    return typer.prompt("Password", hide_input=True, confirmation_prompt=True)


@users_app.command("add")
def add_user(
    username: Annotated[
        str, typer.Option("--username", "-u", prompt=True, help="Login name")
    ],
    role: Annotated[
        Role, typer.Option("--role", "-r", prompt=True, help="Account role")
    ],
    student_id: Annotated[
        int | None,
        typer.Option("--student-id", "-s", help="Student record a student account owns"),
    ] = None,
    password: Annotated[
        str | None,
        typer.Option("--password", "-p", help="Password (asked for when omitted)"),
    ] = None,
) -> None:
    """Create an account that can sign in to the web UI."""
    try:
        user = db.add_user(username, ask_password(password), role, student_id)
    except ValidationError as error:
        report_validation_error(error)
    except ValueError as error:
        fail(str(error))
    console.print(f"[bold green]Account {user.username} created.[/]")


@users_app.command("list")
def list_users() -> None:
    """List every account."""
    accounts = db.list_users()
    if not accounts:
        console.print("[yellow]No accounts found.[/]")
        return

    table = Table(title="Accounts", box=ROUNDED, header_style="bold cyan")
    for column in ("id", "username", "role", "student"):
        table.add_column(
            column.capitalize(), justify="right" if column == "id" else "left"
        )
    for account in accounts:
        table.add_row(
            str(account.id),
            account.username,
            account.role.value,
            "" if account.student_id is None else str(account.student_id),
        )
    console.print(table)


@users_app.command("passwd")
def change_password(
    username: Annotated[
        str, typer.Option("--username", "-u", prompt=True, help="Login name")
    ],
    password: Annotated[
        str | None,
        typer.Option("--password", "-p", help="Password (asked for when omitted)"),
    ] = None,
) -> None:
    """Set a new password for one account."""
    try:
        updated = db.set_user_password(username, ask_password(password))
    except ValueError as error:
        fail(str(error))
    if not updated:
        fail(f"no account with username '{username}'")
    console.print(f"[bold green]Password updated for {username}.[/]")


@users_app.command("remove")
def remove_user(
    username: Annotated[
        str, typer.Option("--username", "-u", prompt=True, help="Login name")
    ],
    yes: Annotated[
        bool, typer.Option("--yes", "-y", help="Skip the confirmation")
    ] = False,
) -> None:
    """Delete one account. It does not delete the student record it owns."""
    if db.get_user_by_username(username) is None:
        fail(f"no account with username '{username}'")
    if not yes and not typer.confirm(f"Delete account {username}?", default=False):
        console.print("[yellow]Cancelled.[/]")
        raise typer.Exit()

    if not db.delete_user(username):
        fail(f"no account with username '{username}'")
    console.print(f"[bold green]Account {username} removed.[/]")


if __name__ == "__main__":
    app()
