# School DB

A small student-management app over SQLite: a SQLModel/Pydantic data model, a Typer
CLI, and a server-rendered FastAPI web UI styled with BeerCSS and powered by HTMX.

## Setup

The project requires Python 3.12 or newer and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
```

`uv sync` installs the runtime dependencies (`fastapi`, `uvicorn`, `jinja2`,
`python-multipart`, `sqlmodel`, `typer`, `rich`) and the development group (`pytest`,
`httpx`).

## Architecture

SQLite remains the database engine. Data is stored in `db.sqlite3`, in the `students`
table with the `id`, `name`, `age`, `birthday`, and `course` columns, and both
interfaces share the same rules and the same persistence layer.

| File | Responsibility |
| --- | --- |
| `models.py` | Defines the SQLModel `Student` table and the Pydantic-backed `StudentUpdate` schema. Shared constraints trim names and courses, reject blank names, restrict age to `1..130`, and require birthdays as real `YYYY-MM-DD` dates. |
| `database.py` | Owns the SQLAlchemy/SQLModel engine, transactional sessions, and CRUD helpers. It contains no presentation logic. |
| `cli.py` | Implements the public Typer commands with Rich output. It translates arguments and delegates all persistence to `database.py`; validation errors are rendered as readable `Error:` messages with exit code 1. |
| `web.py` | Implements the FastAPI routes and renders the Jinja2 templates. Routes translate HTTP requests into calls on `database.py` and never duplicate validation or persistence. |
| `settings.py` | Loads the school branding (name, logo, seed color) from `school.toml` and the `SCHOOL_*` environment variables. |
| `templates/` | `students.html` (the page) plus `partials/` (table body, and the form, delete-confirmation and not-found dialogs). |
| `static/` | `app.css`, `app.js`, `logo.svg`, and `vendor/` with the pinned browser libraries. No external CDN is used at runtime. |
| `odd/tasks/` | The specification and task log for the web phase. |
| `design/student-admin/` | The three design directions; `01-dense-table.html` is the chosen and implemented one. |

## Web UI

```bash
uv run uvicorn web:app --reload
```

Then open <http://127.0.0.1:8000/students>. `uv run python web.py` starts the same
server with reload enabled.

### Routes

| Route | Purpose |
| --- | --- |
| `GET /` | Redirects to `/students`. |
| `GET /students` | Full page. `q` and `course_filter` search the list server-side. |
| `GET /students/rows` | Table body fragment used by the search field and the course select. |
| `GET /students/new` | Add-student dialog. |
| `GET /students/{id}/edit` | Edit dialog prefilled with one student. |
| `GET /students/{id}/delete` | Delete confirmation dialog. |
| `POST /students` | Creates a student. |
| `POST /students/{id}` | Updates a student. |
| `POST /students/{id}/delete` | Deletes a student. |

### Response contract

* HTMX requests (`HX-Request: true`) receive fragments. A successful write swaps the
  table body and sends `HX-Trigger: {"student-changed": true}`; rejected input answers
  `422` with the dialog re-rendered, retargeted to `#dialog-host`; a missing student
  answers `404` with a dialog fragment.
* Plain form posts without HTMX redirect with `303` (Post/Redirect/Get) after a
  successful write, and answer `422` with the full page and the dialog already open
  after rejected input. The GET dialogs render the whole page with the dialog open
  when the request does not come from HTMX, so the app also works with JavaScript
  disabled.
* Invalid input never reaches the database: `models.py` validates before
  `database.py` opens a write, so a rejected request leaves stored data unchanged.

### School branding

`school.toml` configures the UI, and environment variables override it:

```toml
[school]
name = "School DB"
logo = "logo.svg"   # path inside static/
color = "#0b57d0"   # seed for the Material You palette
```

| Variable | Overrides |
| --- | --- |
| `SCHOOL_NAME` | The name in the app bar and the page title. |
| `SCHOOL_LOGO` | The logo image, relative to `static/` (no `..`, no absolute paths). |
| `SCHOOL_COLOR` | The seed color as `#RRGGBB`. |

BeerCSS derives the entire Material You palette (primary, surfaces, containers, and
their contrast pairs) from that single seed color at load time, so the whole UI
follows the school's color.

### Browser assets

HTMX, BeerCSS and its `material-dynamic-colors` dependency are committed under
`static/vendor/` with their pinned versions and SHA-256 checksums in
`static/vendor/README.md`. Icons are inline SVG, so the pages make no external
request at all and work offline.

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

Run one area at a time:

```bash
uv run pytest tests/test_models.py tests/test_database.py tests/test_cli.py
uv run pytest tests/test_web.py tests/test_settings.py
```

All database, CLI and web tests use isolated temporary SQLite files, so they never
modify the project's `db.sqlite3` database.
