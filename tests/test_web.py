"""HTTP-level tests for the FastAPI student CRUD interface."""

from datetime import date

import pytest
from fastapi.testclient import TestClient

import database
import settings
import web


HTMX_HEADERS = {"HX-Request": "true"}
SEEDED_STUDENTS = [
    (1, "Ada Lovelace", 36, date(1815, 12, 10), "Mathematics"),
    (2, "Grace Hopper", 45, date(1906, 12, 9), "Computer Science"),
]


def stored_students() -> list[tuple[int, str, int, date, str]]:
    """Return every persisted student field through the public database API."""
    return [
        (student.id, student.name, student.age, student.birthday, student.course)
        for student in database.get_students()
    ]


@pytest.fixture
def client():
    """Return a client that preserves redirects so each status is observable."""
    test_client = TestClient(web.app, follow_redirects=False)
    try:
        yield test_client
    finally:
        test_client.close()


@pytest.fixture
def seeded_database(isolated_database):
    """Seed the isolated database with two students for list and CRUD tests."""
    database.add_student("Ada Lovelace", 36, "1815-12-10", "Mathematics")
    database.add_student("Grace Hopper", 45, "1906-12-09", "Computer Science")


@pytest.fixture
def custom_branding():
    """Override the cached branding dependency and always remove the override."""
    configured = settings.SchoolSettings(
        name="River City School", logo="custom-logo.svg", color="#123456"
    )
    web.app.dependency_overrides[settings.get_school_settings] = lambda: configured
    try:
        yield configured
    finally:
        web.app.dependency_overrides.pop(settings.get_school_settings, None)


def test_root_redirects_to_students(client, seeded_database) -> None:
    response = client.get("/")

    assert response.status_code == 303
    assert response.headers["location"] == "/students"
    assert stored_students() == SEEDED_STUDENTS


def test_students_page_renders_seeded_rows_and_local_assets(
    client, seeded_database
) -> None:
    response = client.get("/students")

    assert response.status_code == 200
    assert "Ada Lovelace" in response.text
    assert "Grace Hopper" in response.text
    assert "1815-12-10" in response.text
    assert "1906-12-09" in response.text
    assert "2 records" in response.text
    assert 'src="/static/vendor/htmx.min.js"' in response.text
    assert 'href="/static/vendor/beer.min.css"' in response.text
    assert 'href="/static/app.css"' in response.text
    assert 'data-school-color="#0b57d0"' in response.text
    assert stored_students() == SEEDED_STUDENTS


def test_students_page_contains_no_external_urls(client, seeded_database) -> None:
    response = client.get("/students")

    assert response.status_code == 200
    assert response.text
    assert "http://" not in response.text
    assert "https://" not in response.text
    assert stored_students() == SEEDED_STUDENTS


def test_students_page_filters_rows_on_the_server(client, seeded_database) -> None:
    response = client.get(
        "/students", params={"q": "Grace", "course_filter": "Mathematics"}
    )

    assert response.status_code == 200
    assert "No students match this filter." in response.text
    assert "Ada Lovelace" not in response.text
    assert "Grace Hopper" not in response.text
    assert stored_students() == SEEDED_STUDENTS


def test_student_rows_returns_only_matching_htmx_fragment(
    client, seeded_database
) -> None:
    response = client.get(
        "/students/rows",
        params={"q": "Ada", "course_filter": "Mathematics"},
        headers=HTMX_HEADERS,
    )

    assert response.status_code == 200
    assert "Ada Lovelace" in response.text
    assert "Grace Hopper" not in response.text
    assert 'hx-swap-oob="true"' in response.text
    assert stored_students() == SEEDED_STUDENTS


def test_new_student_dialog_returns_an_htmx_form(client, seeded_database) -> None:
    response = client.get("/students/new", headers=HTMX_HEADERS)

    assert response.status_code == 200
    assert "<dialog" in response.text
    assert 'action="/students"' in response.text
    assert stored_students() == SEEDED_STUDENTS


def test_htmx_create_persists_the_new_student(client, seeded_database) -> None:
    response = client.post(
        "/students",
        data={
            "name": "Katherine Johnson",
            "age": "35",
            "birthday": "1918-08-26",
            "course": "Aerospace Engineering",
        },
        headers=HTMX_HEADERS,
    )

    assert response.status_code == 200
    assert response.headers["HX-Trigger"] == '{"student-changed": true}'
    assert "Katherine Johnson" in response.text
    students = database.get_students()
    assert [student.name for student in students] == [
        "Ada Lovelace",
        "Grace Hopper",
        "Katherine Johnson",
    ]
    created = database.get_student(students[-1].id)
    assert created is not None
    assert (created.name, created.age, created.birthday, created.course) == (
        "Katherine Johnson",
        35,
        date(1918, 8, 26),
        "Aerospace Engineering",
    )


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        (
            {
                "name": "Invalid Age",
                "age": "999",
                "birthday": "2010-02-10",
                "course": "Mathematics",
            },
            "130",
        ),
        (
            {
                "name": "",
                "age": "20",
                "birthday": "2010-02-10",
                "course": "Mathematics",
            },
            "at least 1 character",
        ),
        (
            {
                "name": "   ",
                "age": "20",
                "birthday": "2010-02-10",
                "course": "Mathematics",
            },
            "at least 1 character",
        ),
        (
            {
                "name": "Wrong Birthday Format",
                "age": "20",
                "birthday": "10/02/2010",
                "course": "Mathematics",
            },
            "YYYY-MM-DD",
        ),
        (
            {
                "name": "Impossible Birthday",
                "age": "20",
                "birthday": "2010-02-30",
                "course": "Mathematics",
            },
            "valid calendar date",
        ),
    ],
    ids=["age-too-large", "blank-name", "whitespace-name", "bad-date-format", "bad-date"],
)
def test_htmx_invalid_create_never_changes_stored_students(
    client, seeded_database, payload: dict[str, str], message: str
) -> None:
    before = stored_students()

    response = client.post("/students", data=payload, headers=HTMX_HEADERS)

    assert response.status_code == 422
    assert response.headers["HX-Retarget"] == "#dialog-host"
    assert message in response.text
    for field, value in payload.items():
        assert f'name="{field}"' in response.text
        assert f'value="{value}"' in response.text
    assert stored_students() == before
    assert len(stored_students()) == len(SEEDED_STUDENTS)


def test_htmx_edit_dialog_prefills_all_student_fields(
    client, seeded_database
) -> None:
    response = client.get("/students/1/edit", headers=HTMX_HEADERS)

    assert response.status_code == 200
    assert 'value="Ada Lovelace"' in response.text
    assert 'value="36"' in response.text
    assert 'value="1815-12-10"' in response.text
    assert 'value="Mathematics"' in response.text
    assert 'action="/students/1"' in response.text
    assert stored_students() == SEEDED_STUDENTS


def test_htmx_update_persists_every_changed_field(client, seeded_database) -> None:
    response = client.post(
        "/students/1",
        data={
            "name": "Ada King",
            "age": "37",
            "birthday": "1815-12-11",
            "course": "Computing",
        },
        headers=HTMX_HEADERS,
    )

    assert response.status_code == 200
    assert response.headers["HX-Trigger"] == '{"student-changed": true}'
    assert "Ada King" in response.text
    updated = database.get_student(1)
    assert updated is not None
    assert (updated.name, updated.age, updated.birthday, updated.course) == (
        "Ada King",
        37,
        date(1815, 12, 11),
        "Computing",
    )
    assert stored_students() == [
        (1, "Ada King", 37, date(1815, 12, 11), "Computing"),
        SEEDED_STUDENTS[1],
    ]


def test_htmx_invalid_update_leaves_every_stored_field_unchanged(
    client, seeded_database
) -> None:
    before = stored_students()

    response = client.post(
        "/students/1",
        data={
            "name": "Changed Name",
            "age": "0",
            "birthday": "2000-01-01",
            "course": "Changed Course",
        },
        headers=HTMX_HEADERS,
    )

    assert response.status_code == 422
    assert response.headers["HX-Retarget"] == "#dialog-host"
    assert "greater than or equal to 1" in response.text
    assert stored_students() == before
    unchanged = database.get_student(1)
    assert unchanged is not None
    assert (unchanged.name, unchanged.age, unchanged.birthday, unchanged.course) == (
        "Ada Lovelace",
        36,
        date(1815, 12, 10),
        "Mathematics",
    )


def test_htmx_delete_dialog_contains_the_student_name(
    client, seeded_database
) -> None:
    response = client.get("/students/1/delete", headers=HTMX_HEADERS)

    assert response.status_code == 200
    assert "<dialog" in response.text
    assert "<strong>Ada Lovelace</strong>" in response.text
    assert stored_students() == SEEDED_STUDENTS


def test_htmx_delete_removes_the_student(client, seeded_database) -> None:
    response = client.post("/students/1/delete", headers=HTMX_HEADERS)

    assert response.status_code == 200
    assert response.headers["HX-Trigger"] == '{"student-changed": true}'
    assert database.get_student(1) is None
    assert stored_students() == [SEEDED_STUDENTS[1]]


def test_htmx_delete_of_a_missing_student_keeps_the_table_unchanged(
    client, seeded_database
) -> None:
    before = stored_students()

    response = client.post("/students/999999/delete", headers=HTMX_HEADERS)

    assert response.status_code == 404
    assert "not found" in response.text
    assert stored_students() == before
    assert len(stored_students()) == len(SEEDED_STUDENTS)


def test_htmx_edit_of_a_missing_student_returns_a_not_found_fragment(
    client, seeded_database
) -> None:
    before = stored_students()

    response = client.get("/students/999999/edit", headers=HTMX_HEADERS)

    assert response.status_code == 404
    assert "not found" in response.text
    assert stored_students() == before


def test_plain_post_creates_a_student_and_redirects(client, seeded_database) -> None:
    response = client.post(
        "/students",
        data={
            "name": "Mary Jackson",
            "age": "30",
            "birthday": "1990-04-09",
            "course": "Engineering",
        },
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/students"
    students = database.get_students()
    assert [student.name for student in students] == [
        "Ada Lovelace",
        "Grace Hopper",
        "Mary Jackson",
    ]
    created = database.get_student(students[-1].id)
    assert created is not None
    assert (created.name, created.age, created.birthday, created.course) == (
        "Mary Jackson",
        30,
        date(1990, 4, 9),
        "Engineering",
    )


def test_plain_invalid_post_returns_a_full_page_with_an_open_dialog(
    client, seeded_database
) -> None:
    before = stored_students()

    response = client.post(
        "/students",
        data={
            "name": "Invalid Plain Post",
            "age": "999",
            "birthday": "2010-02-10",
            "course": "Mathematics",
        },
    )

    assert response.status_code == 422
    assert "<!doctype html>" in response.text
    assert 'aria-labelledby="student-form-title" open>' in response.text
    assert 'value="Invalid Plain Post"' in response.text
    assert 'value="999"' in response.text
    assert 'value="2010-02-10"' in response.text
    assert 'value="Mathematics"' in response.text
    assert stored_students() == before


def test_plain_edit_of_a_missing_student_redirects_to_students(
    client, seeded_database
) -> None:
    before = stored_students()

    response = client.get("/students/999999/edit")

    assert response.status_code == 303
    assert response.headers["location"] == "/students"
    assert stored_students() == before


def test_importing_the_web_app_preserves_the_public_cli_commands(
    client, seeded_database
) -> None:
    import cli

    command_names = {command.name for command in cli.app.registered_commands}

    assert command_names == {"list", "add", "show", "edit", "delete"}
    assert stored_students() == SEEDED_STUDENTS


def test_custom_branding_is_rendered_on_the_students_page(
    client, seeded_database, custom_branding
) -> None:
    response = client.get("/students")

    assert response.status_code == 200
    assert "River City School" in response.text
    assert 'src="/static/custom-logo.svg"' in response.text
    assert 'data-school-color="#123456"' in response.text
    assert stored_students() == SEEDED_STUDENTS
