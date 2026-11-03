"""FastAPI web UI for the student CRUD, rendered with Jinja2, BeerCSS and HTMX.

This module only translates HTTP requests into calls on ``database.py`` and
renders templates. Validation belongs to ``models.py`` and persistence belongs to
``database.py``, so the web layer never duplicates either.

Response contract
-----------------
* ``GET`` pages use the ``q`` and ``course_filter`` query parameters as the
  current search state.
* HTMX requests (``HX-Request: true``) receive HTML fragments and a
  ``student-changed`` trigger after a successful write.
* Plain form posts without HTMX receive ``303`` redirects on success and a full
  page that renders the dialog with errors on ``422``, so the app still works
  without JavaScript.
* A missing student answers ``404`` with a dialog fragment for HTMX requests.
"""

from collections.abc import Iterable
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError

import database as db
from models import Student
from settings import SchoolSettings, get_school_settings

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

app = FastAPI(title="School DB", description="Student CRUD web UI")
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates.env.globals["available_courses"] = lambda: available_courses(db.get_students())

STUDENT_CHANGED = '{"student-changed": true}'
Settings = Annotated[SchoolSettings, Depends(get_school_settings)]


SQLITE_INTEGER_MAX = 2**63 - 1


def is_htmx(request: Request) -> bool:
    """Report whether the request came from HTMX."""
    return request.headers.get("HX-Request", "").lower() == "true"


def is_stored_id(student_id: int) -> bool:
    """Report whether the identifier can be stored in SQLite's 64-bit integer."""
    return 1 <= student_id <= SQLITE_INTEGER_MAX


def filter_students(
    students: Iterable[Student], query: str = "", course: str = ""
) -> list[Student]:
    """Apply the toolbar filters over an already loaded list of students."""
    term = query.strip().lower()
    selected_course = course.strip()
    result = []
    for student in students:
        if selected_course and student.course != selected_course:
            continue
        haystack = " ".join(
            (str(student.id), student.name, student.birthday.isoformat(), student.course)
        ).lower()
        if term and term not in haystack:
            continue
        result.append(student)
    return result


def available_courses(students: Iterable[Student]) -> list[str]:
    """List the courses present in the database, for the filter select."""
    return sorted({student.course for student in students})


def field_errors(error: ValidationError) -> dict[str, str]:
    """Translate Pydantic failures into one readable message per form field."""
    messages: dict[str, str] = {}
    for item in error.errors():
        location = item["loc"][0] if item["loc"] else "form"
        field = str(location)
        if field in {"name", "age", "birthday", "course"}:
            messages.setdefault(field, item["msg"].removeprefix("Value error, "))
    return messages


def rows_response(
    request: Request,
    students: list[Student],
    query: str,
    course: str,
) -> HTMLResponse:
    """Render the table body fragment, plus the out-of-band record counter."""
    return templates.TemplateResponse(
        request,
        "partials/rows.html",
        {"students": students, "q": query, "course_filter": course, "oob": True},
    )


def dialog_response(
    request: Request, dialog: dict, status_code: int = 200
) -> HTMLResponse:
    """Render one dialog fragment (form, delete confirmation or not-found)."""
    return templates.TemplateResponse(
        request, dialog["template"], {"dialog": dialog}, status_code=status_code
    )


def page_response(
    request: Request,
    settings: SchoolSettings,
    query: str,
    course: str,
    dialog: dict | None = None,
    status_code: int = 200,
) -> HTMLResponse:
    """Render the full students page, optionally with an already open dialog."""
    every_student = db.get_students()
    return templates.TemplateResponse(
        request,
        "students.html",
        {
            "settings": settings,
            "students": filter_students(every_student, query, course),
            "q": query,
            "course_filter": course,
            "dialog": dialog,
        },
        status_code=status_code,
    )


def form_dialog(
    mode: str,
    values: dict[str, str],
    errors: dict[str, str],
    query: str,
    course: str,
    student_id: int | None = None,
    open_dialog: bool = False,
) -> dict:
    """Describe the add/edit dialog so both the page and HTMX can render it."""
    # The key is `fields`, not `values`: Jinja would resolve `dialog.values` to
    # the dict method instead of the mapping.
    return {
        "template": "partials/form.html",
        "mode": mode,
        "student_id": student_id,
        "fields": values,
        "errors": errors,
        "q": query,
        "course_filter": course,
        "open_dialog": open_dialog,
    }


def missing_dialog(student_id: int, query: str, course: str) -> dict:
    """Describe the dialog shown when a student does not exist."""
    return {
        "template": "partials/missing.html",
        "student_id": student_id,
        "q": query,
        "course_filter": course,
    }


def redirect_to_students(query: str = "", course: str = "") -> RedirectResponse:
    """Send a plain (non-HTMX) write back to the list, keeping the filters."""
    parameters = [
        f"{key}={value}"
        for key, value in (("q", query.strip()), ("course_filter", course.strip()))
        if value
    ]
    target = "/students"
    if parameters:
        target = f"{target}?{'&'.join(parameters)}"
    return RedirectResponse(target, status_code=303)


def write_response(
    request: Request, settings: SchoolSettings, query: str, course: str
) -> Response:
    """Answer a write: fragments with a trigger for HTMX, a redirect otherwise."""
    if is_htmx(request):
        response = rows_response(
            request, filter_students(db.get_students(), query, course), query, course
        )
        response.headers["HX-Trigger"] = STUDENT_CHANGED
        return response
    # Post/Redirect/Get, so a refresh never repeats the write.
    return redirect_to_students(query, course)


def invalid_form_response(
    request: Request,
    settings: SchoolSettings,
    mode: str,
    values: dict[str, str],
    error: ValidationError,
    query: str,
    course: str,
    student_id: int | None,
) -> HTMLResponse:
    """Re-render the form with field errors and status 422."""
    errors = field_errors(error)
    dialog = form_dialog(
        mode,
        values,
        errors,
        query,
        course,
        student_id=student_id,
        open_dialog=not is_htmx(request),
    )
    if is_htmx(request):
        response = dialog_response(request, dialog, status_code=422)
        response.headers["HX-Retarget"] = "#dialog-host"
        response.headers["HX-Reswap"] = "innerHTML"
        return response
    return page_response(
        request, settings, query, course, dialog=dialog, status_code=422
    )


def missing_student_response(
    request: Request,
    settings: SchoolSettings,
    student_id: int,
    query: str,
    course: str,
) -> HTMLResponse:
    """Answer a request about a student that does not exist."""
    if is_htmx(request):
        response = dialog_response(
            request, missing_dialog(student_id, query, course), status_code=404
        )
        response.headers["HX-Retarget"] = "#dialog-host"
        response.headers["HX-Reswap"] = "innerHTML"
        return response
    return redirect_to_students(query, course)


@app.get("/")
def index() -> RedirectResponse:
    """Send the browser to the students list."""
    return RedirectResponse("/students", status_code=303)


@app.get("/students", response_class=HTMLResponse)
def students_page(
    request: Request,
    settings: Settings,
    q: str = "",
    course_filter: str = "",
) -> HTMLResponse:
    """Full students page with the table rendered server-side."""
    return page_response(request, settings, q, course_filter)


@app.get("/students/rows", response_class=HTMLResponse)
def student_rows(request: Request, q: str = "", course_filter: str = "") -> HTMLResponse:
    """Table body fragment used by the search and course filters."""
    return rows_response(
        request, filter_students(db.get_students(), q, course_filter), q, course_filter
    )


@app.get("/students/new", response_class=HTMLResponse)
def new_student_dialog(
    request: Request,
    settings: Settings,
    q: str = "",
    course_filter: str = "",
) -> HTMLResponse:
    """Empty add-student dialog: a fragment for HTMX, an open page otherwise."""
    dialog = form_dialog(
        "create",
        {"name": "", "age": "", "birthday": "", "course": ""},
        {},
        q,
        course_filter,
        open_dialog=not is_htmx(request),
    )
    if is_htmx(request):
        return dialog_response(request, dialog)
    return page_response(request, settings, q, course_filter, dialog=dialog)


@app.get("/students/{student_id}/edit", response_class=HTMLResponse)
def edit_student_dialog(
    request: Request,
    student_id: int,
    settings: Settings,
    q: str = "",
    course_filter: str = "",
) -> HTMLResponse:
    """Edit dialog prefilled with one student."""
    if not is_stored_id(student_id):
        return missing_student_response(request, settings, student_id, q, course_filter)
    student = db.get_student(student_id)
    if student is None:
        return missing_student_response(request, settings, student_id, q, course_filter)
    values = {
        "name": student.name,
        "age": str(student.age),
        "birthday": student.birthday.isoformat(),
        "course": student.course,
    }
    dialog = form_dialog(
        "edit",
        values,
        {},
        q,
        course_filter,
        student_id=student_id,
        open_dialog=not is_htmx(request),
    )
    if is_htmx(request):
        return dialog_response(request, dialog)
    return page_response(request, settings, q, course_filter, dialog=dialog)


@app.get("/students/{student_id}/delete", response_class=HTMLResponse)
def delete_student_dialog(
    request: Request,
    student_id: int,
    settings: Settings,
    q: str = "",
    course_filter: str = "",
) -> HTMLResponse:
    """Confirmation dialog shown before deleting one student."""
    if not is_stored_id(student_id):
        return missing_student_response(request, settings, student_id, q, course_filter)
    student = db.get_student(student_id)
    if student is None:
        return missing_student_response(request, settings, student_id, q, course_filter)
    dialog = {
        "template": "partials/confirm.html",
        "student": student,
        "q": q,
        "course_filter": course_filter,
        "open_dialog": not is_htmx(request),
    }
    if is_htmx(request):
        return dialog_response(request, dialog)
    return page_response(request, settings, q, course_filter, dialog=dialog)


@app.post("/students", response_class=HTMLResponse)
def create_student(
    request: Request,
    settings: Settings,
    name: Annotated[str, Form()] = "",
    age: Annotated[str, Form()] = "",
    birthday: Annotated[str, Form()] = "",
    course: Annotated[str, Form()] = "",
    q: Annotated[str, Form()] = "",
    course_filter: Annotated[str, Form()] = "",
) -> HTMLResponse:
    """Validate and persist a new student."""
    values = {"name": name, "age": age, "birthday": birthday, "course": course}
    try:
        db.add_student(name, age, birthday, course)
    except ValidationError as error:
        return invalid_form_response(
            request, settings, "create", values, error, q, course_filter, None
        )
    return write_response(request, settings, q, course_filter)


@app.post("/students/{student_id}", response_class=HTMLResponse)
def update_student(
    request: Request,
    student_id: int,
    settings: Settings,
    name: Annotated[str, Form()] = "",
    age: Annotated[str, Form()] = "",
    birthday: Annotated[str, Form()] = "",
    course: Annotated[str, Form()] = "",
    q: Annotated[str, Form()] = "",
    course_filter: Annotated[str, Form()] = "",
) -> HTMLResponse:
    """Validate and apply an update to one student."""
    if not is_stored_id(student_id):
        return missing_student_response(request, settings, student_id, q, course_filter)
    values = {"name": name, "age": age, "birthday": birthday, "course": course}
    try:
        student = db.edit_student(
            student_id, name=name, age=age, birthday=birthday, course=course
        )
    except ValidationError as error:
        return invalid_form_response(
            request, settings, "edit", values, error, q, course_filter, student_id
        )
    if student is None:
        return missing_student_response(request, settings, student_id, q, course_filter)
    return write_response(request, settings, q, course_filter)


@app.post("/students/{student_id}/delete", response_class=HTMLResponse)
def remove_student(
    request: Request,
    student_id: int,
    settings: Settings,
    q: Annotated[str, Form()] = "",
    course_filter: Annotated[str, Form()] = "",
) -> HTMLResponse:
    """Delete one student after the confirmation dialog."""
    if not is_stored_id(student_id):
        return missing_student_response(request, settings, student_id, q, course_filter)
    if not db.delete_student(student_id):
        return missing_student_response(request, settings, student_id, q, course_filter)
    return write_response(request, settings, q, course_filter)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("web:app", reload=True)
