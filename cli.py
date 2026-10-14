"""Student CLI over database.py (typer + rich).

Golden rule for this file: zero SQL. Every data access goes through
database.py; here we only translate command-line arguments into calls and
render the result with rich.
"""

from datetime import date
from typing import Annotated

import typer
from rich.box import ROUNDED
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

import database as db

app = typer.Typer(help="Student CRUD over SQLite.", no_args_is_help=True)
console = Console()

# database.py still returns plain tuples (SELECT * without row_factory), so the
# column order lives here. Once you add row_factory to database.py, these two
# lines become dict(zip(...)) over a Row.
COLUMNS = ("id", "name", "age", "birthday", "course")

RIGHT_ALIGNED = {"id", "age"}


# --- presentation and validation helpers ---
def fail(message: str) -> None:
    """Print a readable error and stop with exit code 1."""
    console.print(f"[bold red]Error:[/] {message}")
    raise typer.Exit(code=1)


def to_dict(row: tuple) -> dict:
    return dict(zip(COLUMNS, row))


def validate_name(name: str) -> str:
    clean = name.strip()
    if not clean:
        fail("the name cannot be empty")
    return clean


def validate_age(age: int) -> int:
    if not 1 <= age <= 130:
        fail(f"age must be between 1 and 130, got {age}")
    return age


def validate_birthday(birthday: str) -> str:
    try:
        date.fromisoformat(birthday)
    except ValueError:
        fail(f"birthday must use the YYYY-MM-DD format, got '{birthday}'")
    return birthday


def render_table(students: list[dict]) -> None:
    if not students:
        console.print("[yellow]No students found.[/]")
        return

    table = Table(title="Students", box=ROUNDED, header_style="bold cyan")
    for column in COLUMNS:
        table.add_column(
            column.capitalize(),
            justify="right" if column in RIGHT_ALIGNED else "left",
        )
    for student in students:
        table.add_row(*[str(student[column]) for column in COLUMNS])
    console.print(table)


def require_existing(student_id: int) -> dict:
    """database.py still does not return a rowcount on update/delete, so the CLI
    checks existence before mutating in order to be able to report the truth."""
    row = db.get_student(student_id)
    if row is None:
        fail(f"no student with id {student_id}")
    return to_dict(row)


# --- commands ---
@app.command("list")
def list_students() -> None:
    """List every student."""
    render_table([to_dict(row) for row in db.get_students()])


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
    new_id = db.add_student(
        validate_name(name), validate_age(age), validate_birthday(birthday), course.strip()
    )
    console.print(f"[bold green]Student {new_id} created.[/]")


@app.command("show")
def show_student(
    student_id: Annotated[int, typer.Argument(help="Student ID")],
) -> None:
    """Show a single student."""
    student = require_existing(student_id)
    body = "\n".join(f"{column:<10}{student[column]}" for column in COLUMNS)
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
        fields["name"] = validate_name(name)
    if age is not None:
        fields["age"] = validate_age(age)
    if birthday is not None:
        fields["birthday"] = validate_birthday(birthday)
    if course is not None:
        fields["course"] = course.strip()

    if not fields:
        fail("you did not pass any field; use --name, --age, --birthday or --course")

    require_existing(student_id)
    db.edit_student(student_id, **fields)
    console.print(f"[bold green]Student {student_id} updated.[/]")


@app.command("delete")
def delete_student(
    student_id: Annotated[int, typer.Argument(help="Student ID")],
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip the confirmation")] = False,
) -> None:
    """Delete a student."""
    require_existing(student_id)
    if not yes and not typer.confirm(f"Delete student {student_id}?", default=False):
        console.print("[yellow]Cancelled.[/]")
        raise typer.Exit()

    db.delete_student(student_id)
    console.print(f"[bold green]Student {student_id} deleted.[/]")


if __name__ == "__main__":
    app()
