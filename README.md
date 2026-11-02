# School BD

A small student-management CLI that keeps SQLite as its storage engine while using SQLModel and Pydantic for the data model, validation, and persistence layer.

## Setup

The project requires Python 3.12 or newer and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
uv run python cli.py --help
```

`uv sync` installs both the runtime dependencies (`sqlmodel`, `typer`, and `rich`) and the development dependency group (`pytest`).

## Architecture

SQLite remains the database engine. Data is stored in the existing `db.sqlite3` file and the existing `students` table with the `id`, `name`, `age`, `birthday`, and `course` columns.

| File | Responsibility |
| --- | --- |
| `models.py` | Defines the SQLModel `Student` table and Pydantic-backed `StudentUpdate` schema. Shared constraints trim names and courses, reject blank names, restrict age to `1..130`, and require birthday values in `YYYY-MM-DD` format. |
| `database.py` | Owns the SQLAlchemy/SQLModel engine, transactional sessions, and CRUD helpers. It does not contain presentation logic. |
| `cli.py` | Implements the public Typer commands with Rich output. It translates arguments and delegates all persistence to `database.py`; validation errors are rendered as readable `Error:` messages with exit code 1. |

The current implementation keeps the web phase out of scope: FastAPI, BeerCSS, HTMX, and web endpoints are not included.

## CLI usage

Run commands with:

```bash
uv run python cli.py <command> [options]
```

### `list`

List every student in a table.

```bash
uv run python cli.py list
```

### `add`

Create a student. The command prompts for any option that is not supplied.

```bash
uv run python cli.py add \
  --name "Ada Lovelace" \
  --age 36 \
  --birthday 1815-12-10 \
  --course Mathematics
```

### `show`

Show one student by numeric ID.

```bash
uv run python cli.py show 1
```

### `edit`

Update one or more fields of an existing student.

```bash
uv run python cli.py edit 1 --name "Grace Hopper" --age 37
```

### `delete`

Delete a student after confirmation. Use `--yes` to skip the confirmation prompt.

```bash
uv run python cli.py delete 1
uv run python cli.py delete 1 --yes
```

## Tests

Run the complete test suite with:

```bash
uv run pytest
```

Run the focused model, persistence, and public-CLI tests with:

```bash
uv run pytest tests/test_models.py tests/test_database.py tests/test_cli.py
```

All database and CLI tests use isolated temporary SQLite files, so they never modify the project's `db.sqlite3` database.
