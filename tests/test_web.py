"""HTTP-level tests for the FastAPI student CRUD interface and its sign-in."""

import pathlib
import re
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

import database
import settings
import web
from models import Role


HTMX_HEADERS = {"HX-Request": "true"}
PASSWORD = "una-clave-larga"
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


def sign_in(
    test_client: TestClient,
    username: str,
    password: str = PASSWORD,
    next_path: str | None = None,
):
    """Post the login form the way the page does."""
    data = {"username": username, "password": password}
    if next_path is not None:
        data["next"] = next_path
    return test_client.post("/login", data=data)


@pytest.fixture
def anonymous_client():
    """A client with no session at all: the shape every guard test starts from."""
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


# One account per role exists, and each fixture makes only the account its test needs:
# hashing a password with scrypt is deliberately expensive, so creating three of them
# in every test would spend most of the suite on setup.


@pytest.fixture
def teacher(seeded_database):
    """The teacher account a page test signs in with."""
    return database.add_user("teacher.one", PASSWORD, Role.teacher)


@pytest.fixture
def admin(seeded_database):
    """The account whose role adds nothing to a teacher's powers yet."""
    return database.add_user("admin.one", PASSWORD, Role.admin)


@pytest.fixture
def student_account(seeded_database):
    """The account that owns the first seeded student."""
    return database.add_user("ada.lovelace", PASSWORD, Role.student, student_id=1)


@pytest.fixture
def teacher_client(teacher):
    """A client already signed in as a teacher: the student CRUD now needs a role."""
    with TestClient(web.app, follow_redirects=False) as test_client:
        sign_in(test_client, "teacher.one")
        yield test_client


@pytest.fixture
def admin_client(admin):
    """A client already signed in as an administrator."""
    with TestClient(web.app, follow_redirects=False) as test_client:
        sign_in(test_client, "admin.one")
        yield test_client


@pytest.fixture
def student_client(student_account):
    """A client already signed in as the student that owns the first record."""
    with TestClient(web.app, follow_redirects=False) as test_client:
        sign_in(test_client, "ada.lovelace")
        yield test_client


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


def test_teacher_hub_has_only_the_students_card(
    teacher_client, seeded_database
) -> None:
    response = teacher_client.get("/")

    assert response.status_code == 200
    assert re.findall(
        r'<a class="role-card" href="([^"]+)">', response.text
    ) == ["/students"]
    assert 'href="/accounts"' not in response.text
    assert 'href="/branding"' not in response.text
    assert stored_students() == SEEDED_STUDENTS


def test_admin_hub_has_students_accounts_and_branding_cards(
    admin_client, seeded_database
) -> None:
    response = admin_client.get("/")

    assert response.status_code == 200
    assert re.findall(
        r'<a class="role-card" href="([^"]+)">', response.text
    ) == ["/students", "/accounts", "/branding"]
    assert stored_students() == SEEDED_STUDENTS


def test_students_page_renders_seeded_rows_and_local_assets(
    teacher_client, seeded_database
) -> None:
    response = teacher_client.get("/students")

    assert response.status_code == 200
    assert "Ada Lovelace" in response.text
    assert "Grace Hopper" in response.text
    assert "1815-12-10" in response.text
    assert "1906-12-09" in response.text
    assert "2 records" in response.text
    assert re.search(r'src="/static/vendor/htmx\.min\.js\?v=[0-9a-f]{12}"', response.text)
    assert re.search(r'href="/static/vendor/beer\.min\.css\?v=[0-9a-f]{12}"', response.text)
    assert re.search(r'href="/static/app\.css\?v=[0-9a-f]{12}"', response.text)
    assert 'data-theme-source="' in response.text
    assert 'data-theme-fallback="' in response.text
    assert stored_students() == SEEDED_STUDENTS


def test_students_page_contains_no_external_urls(teacher_client, seeded_database) -> None:
    response = teacher_client.get("/students")

    assert response.status_code == 200
    assert response.text
    assert "http://" not in response.text
    assert "https://" not in response.text
    assert stored_students() == SEEDED_STUDENTS


def test_students_page_filters_rows_on_the_server(teacher_client, seeded_database) -> None:
    response = teacher_client.get(
        "/students", params={"q": "Grace", "course_filter": "Mathematics"}
    )

    assert response.status_code == 200
    assert "No students match this filter." in response.text
    assert "Ada Lovelace" not in response.text
    assert "Grace Hopper" not in response.text
    assert stored_students() == SEEDED_STUDENTS


def test_student_rows_returns_only_matching_htmx_fragment(
    teacher_client, seeded_database
) -> None:
    response = teacher_client.get(
        "/students/rows",
        params={"q": "Ada", "course_filter": "Mathematics"},
        headers=HTMX_HEADERS,
    )

    assert response.status_code == 200
    assert "Ada Lovelace" in response.text
    assert "Grace Hopper" not in response.text
    assert 'hx-swap-oob="true"' in response.text
    assert stored_students() == SEEDED_STUDENTS


def test_new_student_dialog_returns_an_htmx_form(teacher_client, seeded_database) -> None:
    response = teacher_client.get("/students/new", headers=HTMX_HEADERS)

    assert response.status_code == 200
    assert "<dialog" in response.text
    assert 'action="/students"' in response.text
    assert stored_students() == SEEDED_STUDENTS


def test_htmx_create_persists_the_new_student(teacher_client, seeded_database) -> None:
    response = teacher_client.post(
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
    teacher_client, seeded_database, payload: dict[str, str], message: str
) -> None:
    before = stored_students()

    response = teacher_client.post("/students", data=payload, headers=HTMX_HEADERS)

    assert response.status_code == 422
    assert response.headers["HX-Retarget"] == "#dialog-host"
    assert message in response.text
    for field, value in payload.items():
        assert f'name="{field}"' in response.text
        assert f'value="{value}"' in response.text
    assert stored_students() == before
    assert len(stored_students()) == len(SEEDED_STUDENTS)


def test_htmx_edit_dialog_prefills_all_student_fields(
    teacher_client, seeded_database
) -> None:
    response = teacher_client.get("/students/1/edit", headers=HTMX_HEADERS)

    assert response.status_code == 200
    assert 'value="Ada Lovelace"' in response.text
    assert 'value="36"' in response.text
    assert 'value="1815-12-10"' in response.text
    assert 'value="Mathematics"' in response.text
    assert 'action="/students/1"' in response.text
    assert stored_students() == SEEDED_STUDENTS


def test_htmx_update_persists_every_changed_field(teacher_client, seeded_database) -> None:
    response = teacher_client.post(
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
    teacher_client, seeded_database
) -> None:
    before = stored_students()

    response = teacher_client.post(
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
    teacher_client, seeded_database
) -> None:
    response = teacher_client.get("/students/1/delete", headers=HTMX_HEADERS)

    assert response.status_code == 200
    assert "<dialog" in response.text
    assert "<strong>Ada Lovelace</strong>" in response.text
    assert stored_students() == SEEDED_STUDENTS


def test_htmx_delete_removes_the_student(teacher_client, seeded_database) -> None:
    response = teacher_client.post("/students/1/delete", headers=HTMX_HEADERS)

    assert response.status_code == 200
    assert response.headers["HX-Trigger"] == '{"student-changed": true}'
    assert database.get_student(1) is None
    assert stored_students() == [SEEDED_STUDENTS[1]]


def test_htmx_delete_of_a_missing_student_keeps_the_table_unchanged(
    teacher_client, seeded_database
) -> None:
    before = stored_students()

    response = teacher_client.post("/students/999999/delete", headers=HTMX_HEADERS)

    assert response.status_code == 404
    assert "not found" in response.text
    assert stored_students() == before
    assert len(stored_students()) == len(SEEDED_STUDENTS)


def test_htmx_edit_of_a_missing_student_returns_a_not_found_fragment(
    teacher_client, seeded_database
) -> None:
    before = stored_students()

    response = teacher_client.get("/students/999999/edit", headers=HTMX_HEADERS)

    assert response.status_code == 404
    assert "not found" in response.text
    assert stored_students() == before


def test_plain_post_creates_a_student_and_redirects(teacher_client, seeded_database) -> None:
    response = teacher_client.post(
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
    teacher_client, seeded_database
) -> None:
    before = stored_students()

    response = teacher_client.post(
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
    teacher_client, seeded_database
) -> None:
    before = stored_students()

    response = teacher_client.get("/students/999999/edit")

    assert response.status_code == 303
    assert response.headers["location"] == "/students"
    assert stored_students() == before


def test_importing_the_web_app_preserves_the_public_cli_commands(
    teacher_client, seeded_database
) -> None:
    import cli

    command_names = {command.name for command in cli.app.registered_commands}
    group_names = {group.name for group in cli.app.registered_groups}

    assert command_names == {"list", "add", "show", "edit", "delete"}
    assert group_names == {"users"}
    assert stored_students() == SEEDED_STUDENTS


def test_custom_branding_is_rendered_on_the_students_page(
    teacher_client, seeded_database, custom_branding
) -> None:
    response = teacher_client.get("/students")

    assert response.status_code == 200
    assert "River City School" in response.text
    assert 'src="/static/custom-logo.svg"' in response.text
    assert 'data-theme-source="/static/custom-logo.svg"' in response.text
    assert 'data-theme-fallback="#123456"' in response.text
    assert stored_students() == SEEDED_STUDENTS


def test_palette_setting_selects_the_theme_source_on_the_page(
    teacher_client, seeded_database
) -> None:
    configured = settings.SchoolSettings(
        name="River City School",
        logo="custom-logo.svg",
        color="#123456",
        palette="color",
    )
    web.app.dependency_overrides[settings.get_school_settings] = lambda: configured
    try:
        response = teacher_client.get("/students")
    finally:
        web.app.dependency_overrides.pop(settings.get_school_settings, None)

    assert response.status_code == 200
    assert 'data-theme-source="#123456"' in response.text
    assert 'data-theme-fallback="#123456"' in response.text
    assert stored_students() == SEEDED_STUDENTS


@pytest.mark.parametrize("student_id", [-1, 0, 2**63, 10**20])
def test_htmx_requests_for_ids_outside_sqlite_range_return_not_found(
    teacher_client, seeded_database, student_id
) -> None:
    """SQLite stores identifiers as signed 64-bit integers."""
    response = teacher_client.get(f"/students/{student_id}/edit", headers=HTMX_HEADERS)

    assert response.status_code == 404
    assert "not found" in response.text.lower()


@pytest.mark.parametrize("student_id", [2**63, 10**20])
def test_writes_for_ids_outside_sqlite_range_never_touch_the_table(
    teacher_client, seeded_database, student_id
) -> None:
    before = stored_students()

    update = teacher_client.post(
        f"/students/{student_id}",
        data={"name": "Huge", "age": "10", "birthday": "2011-01-01", "course": "X"},
        headers=HTMX_HEADERS,
    )
    delete = teacher_client.post(f"/students/{student_id}/delete", data={}, headers=HTMX_HEADERS)

    assert update.status_code == 404
    assert delete.status_code == 404
    assert stored_students() == before


def test_plain_request_for_an_id_outside_sqlite_range_redirects(teacher_client, seeded_database) -> None:
    response = teacher_client.get(f"/students/{10**20}/edit")

    assert response.status_code == 303
    assert response.headers["location"] == "/students"


def test_vendored_stylesheets_reference_only_files_that_exist() -> None:
    """A browser fetches every url() a stylesheet declares, matched or not.

    BeerCSS shipped 45 references to shape masks and icon fonts that this project
    does not vendor, which cost 41 `404` requests on every page load.
    """
    vendor = pathlib.Path(web.BASE_DIR) / "static" / "vendor"
    missing = []
    for stylesheet in sorted(vendor.glob("*.css")):
        for reference in re.findall(r"url\(\s*([^)'\"]+?)\s*\)", stylesheet.read_text()):
            if reference.startswith("data:"):
                continue
            if not (stylesheet.parent / reference).exists():
                missing.append(f"{stylesheet.name}: {reference}")

    assert missing == []


def test_the_login_page_asks_for_a_username_and_a_password(
    anonymous_client, teacher
) -> None:
    response = anonymous_client.get("/login")

    assert response.status_code == 200
    assert 'action="/login"' in response.text
    assert 'name="username"' in response.text
    assert 'type="password"' in response.text
    assert "Ada Lovelace" not in response.text
    assert "Grace Hopper" not in response.text
    assert "https://" not in response.text
    for internal_name in ("db.sqlite3", "models.py", "web.py", "SQLite", "CLI"):
        assert internal_name not in response.text


def test_anonymous_visitors_are_sent_to_the_login_page_and_change_nothing(
    anonymous_client, teacher
) -> None:
    before = stored_students()

    for path in (
        "/students",
        "/students/rows",
        "/students/new",
        "/students/1/edit",
        "/students/1/delete",
        "/me",
    ):
        response = anonymous_client.get(path)
        assert response.status_code == 303, path
        assert response.headers["location"] == f"/login?next={path}"

    created = anonymous_client.post(
        "/students",
        data={"name": "Nobody", "age": "10", "birthday": "2011-01-01", "course": "X"},
    )
    updated = anonymous_client.post("/students/1", data={"name": "Nobody"})
    deleted = anonymous_client.post("/students/1/delete", data={})

    assert created.status_code == updated.status_code == deleted.status_code == 303
    assert stored_students() == before


def test_a_teacher_signs_in_and_reaches_the_student_admin(
    anonymous_client, teacher
) -> None:
    response = sign_in(anonymous_client, "TEACHER.ONE")

    assert response.status_code == 303
    assert response.headers["location"] == "/"
    cookie = response.headers["set-cookie"].lower()
    assert "school_session=" in cookie
    assert "httponly" in cookie
    assert "samesite=lax" in cookie
    assert "path=/" in cookie
    assert "max-age=" in cookie

    page = anonymous_client.get("/")
    assert page.status_code == 200
    assert "Students" in page.text
    assert "teacher.one" in page.text
    assert "Sign out" in page.text

    student_admin = anonymous_client.get("/students")
    assert student_admin.status_code == 200
    assert "Ada Lovelace" in student_admin.text


def test_an_admin_signs_in_and_reaches_the_role_hub(
    anonymous_client, admin
) -> None:
    response = sign_in(anonymous_client, "admin.one")

    assert response.status_code == 303
    assert response.headers["location"] == "/"

    page = anonymous_client.get("/")
    assert page.status_code == 200
    assert "Students" in page.text
    assert "Accounts" in page.text
    assert "Branding" in page.text
    assert "admin.one" in page.text
    assert "Sign out" in page.text

    student_admin = anonymous_client.get("/students")
    assert student_admin.status_code == 200
    assert "Ada Lovelace" in student_admin.text


def test_bad_credentials_are_refused_and_open_no_session(
    anonymous_client, teacher
) -> None:
    before = stored_students()

    response = sign_in(anonymous_client, "teacher.one", password="clave-incorrecta")

    assert response.status_code == 401
    assert "set-cookie" not in response.headers
    assert "not correct" in response.text.lower()
    assert "Traceback" not in response.text

    still_outside = anonymous_client.get("/students")
    assert still_outside.status_code == 303
    assert stored_students() == before


def test_an_unknown_username_is_refused_like_a_wrong_password(
    anonymous_client, teacher
) -> None:
    unknown = sign_in(anonymous_client, "nadie.aqui")
    wrong = sign_in(anonymous_client, "teacher.one", password="clave-incorrecta")

    assert unknown.status_code == wrong.status_code == 401
    assert "set-cookie" not in unknown.headers
    assert "set-cookie" not in wrong.headers
    assert "not correct" in unknown.text.lower()
    assert "not correct" in wrong.text.lower()


def test_a_student_signs_in_and_sees_only_their_own_record(
    student_client
) -> None:
    response = student_client.get("/me")

    assert response.status_code == 200
    assert "Ada Lovelace" in response.text
    assert "Grace Hopper" not in response.text
    assert "ada.lovelace" in response.text


def test_a_student_cannot_reach_the_student_admin(student_client) -> None:
    before = stored_students()

    for path in (
        "/students",
        "/students/rows",
        "/students/new",
        "/students/1/edit",
        "/students/1/delete",
    ):
        response = student_client.get(path)
        assert response.status_code == 403, path

    created = student_client.post(
        "/students",
        data={"name": "Nobody", "age": "10", "birthday": "2011-01-01", "course": "X"},
    )
    updated = student_client.post("/students/1", data={"name": "Nobody"})
    deleted = student_client.post("/students/1/delete", data={})

    assert created.status_code == updated.status_code == deleted.status_code == 403
    assert stored_students() == before


def test_a_teacher_cannot_reach_the_student_page(teacher_client) -> None:
    response = teacher_client.get("/me")

    assert response.status_code == 403


def test_signing_in_again_sends_you_to_your_own_home(
    teacher_client, student_client
) -> None:
    teacher_page = teacher_client.get("/login")
    student_page = student_client.get("/login")

    assert teacher_page.status_code == 303
    assert teacher_page.headers["location"] == "/"
    assert student_page.status_code == 303
    assert student_page.headers["location"] == "/me"


def test_the_root_sends_every_visitor_to_their_own_place(
    anonymous_client, teacher_client, student_client
) -> None:
    anonymous = anonymous_client.get("/")
    teacher = teacher_client.get("/")
    student = student_client.get("/")

    assert anonymous.status_code == 303
    assert anonymous.headers["location"] == "/login"
    assert teacher.status_code == 200
    assert "Good morning, teacher.one" in teacher.text
    assert student.status_code == 303
    assert student.headers["location"] == "/me"


def test_role_hubs_never_leak_student_records(
    teacher_client, admin_client
) -> None:
    for page in (teacher_client.get("/"), admin_client.get("/")):
        assert page.status_code == 200
        assert "Ada Lovelace" not in page.text
        assert "Grace Hopper" not in page.text


def test_the_signed_in_account_is_a_plain_label_in_every_top_bar(
    teacher_client, student_client
) -> None:
    pages = (
        (teacher_client.get("/"), "teacher.one"),
        (teacher_client.get("/students"), "teacher.one"),
        (student_client.get("/me"), "ada.lovelace"),
    )

    for page, username in pages:
        assert page.status_code == 200
        assert f'<span class="account-label">{username}</span>' in page.text
        assert f'<span class="chip">{username}</span>' not in page.text
        assert 'method="post" action="/logout"' in page.text


def test_the_role_hub_hides_internal_names_and_external_urls(
    teacher_client
) -> None:
    response = teacher_client.get("/")

    assert response.status_code == 200
    assert "http://" not in response.text
    assert "https://" not in response.text
    for internal_name in (
        "db.sqlite3",
        "models.py",
        "web.py",
        "SQLite",
        "CLI",
        "BeerCSS",
    ):
        assert internal_name not in response.text


def test_logout_closes_the_session_everywhere(teacher_client) -> None:
    stolen = teacher_client.cookies["school_session"]

    response = teacher_client.post("/logout")

    assert response.status_code == 303
    assert response.headers["location"] == "/login"

    replayed = teacher_client.get(
        "/students", headers={"Cookie": f"school_session={stolen}"}
    )
    assert replayed.status_code == 303
    assert replayed.headers["location"] == "/login?next=/students"


def test_an_expired_session_is_refused_and_forgotten(anonymous_client, teacher) -> None:
    expired = database.create_session(teacher.id, ttl=timedelta(seconds=-1))

    response = anonymous_client.get(
        "/students", headers={"Cookie": f"school_session={expired}"}
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/login?next=/students"
    assert database.delete_session(expired) is False


def test_a_forged_cookie_opens_nothing(anonymous_client, teacher) -> None:
    response = anonymous_client.get(
        "/students", headers={"Cookie": "school_session=not-a-real-token"}
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/login?next=/students"


def test_the_next_parameter_cannot_leave_this_site(anonymous_client, teacher) -> None:
    offsite = sign_in(anonymous_client, "teacher.one", next_path="https://evil.example/")
    local = sign_in(anonymous_client, "teacher.one", next_path="/students?q=Ada")

    assert offsite.status_code == 303
    assert offsite.headers["location"] == "/"
    assert local.status_code == 303
    assert local.headers["location"] == "/students?q=Ada"


def test_signing_in_reaches_the_page_that_asked_for_it(anonymous_client, teacher) -> None:
    bounced = anonymous_client.get("/students/2/edit")
    assert bounced.headers["location"] == "/login?next=/students/2/edit"

    signed_in = sign_in(
        anonymous_client, "teacher.one", next_path="/students/2/edit"
    )

    assert signed_in.status_code == 303
    assert signed_in.headers["location"] == "/students/2/edit"
    assert "Grace Hopper" in anonymous_client.get("/students/2/edit").text


def test_a_student_whose_record_is_gone_still_gets_a_readable_page(
    student_client
) -> None:
    assert database.delete_student(1) is True

    response = student_client.get("/me")

    assert response.status_code == 404
    assert "Traceback" not in response.text
    assert "ada.lovelace" in response.text


def test_a_student_never_sees_another_student_in_the_top_bar(
    student_client
) -> None:
    page = student_client.get("/me")

    assert "My record" in page.text
    assert 'href="/students"' not in page.text
    assert "Computer Science" not in page.text


# --- The admin's accounts panel (odd/tasks/role-panels.md T2) ---


@pytest.fixture
def roster(seeded_database):
    """One account per role, for the accounts table."""
    teacher = database.add_user("teacher.one", PASSWORD, Role.teacher)
    admin = database.add_user("admin.one", PASSWORD, Role.admin)
    student = database.add_user("ada.lovelace", PASSWORD, Role.student, student_id=1)
    return {"teacher": teacher, "admin": admin, "student": student}


@pytest.fixture
def accounts_client(roster):
    """A client already signed in as the roster's administrator."""
    with TestClient(web.app, follow_redirects=False) as test_client:
        sign_in(test_client, "admin.one")
        yield test_client


@pytest.fixture
def roster_teacher_client(roster):
    """A client already signed in as the roster's teacher."""
    with TestClient(web.app, follow_redirects=False) as test_client:
        sign_in(test_client, "teacher.one")
        yield test_client


def stored_accounts() -> list[tuple[str, str, int | None]]:
    """Return every persisted account field through the public database API."""
    return [
        (entry.username, entry.role.value, entry.student_id)
        for entry in database.list_users()
    ]


def test_an_admin_lists_every_account(accounts_client) -> None:
    response = accounts_client.get("/accounts")

    assert response.status_code == 200
    for username in ("teacher.one", "admin.one", "ada.lovelace"):
        assert username in response.text
    assert "teacher" in response.text
    assert "student" in response.text
    assert "admin" in response.text
    assert "Ada Lovelace (1)" in response.text
    assert stored_students() == SEEDED_STUDENTS


def test_the_accounts_panel_is_admin_only(
    anonymous_client, teacher_client, student_client
) -> None:
    anonymous = anonymous_client.get("/accounts")
    assert anonymous.status_code == 303
    assert anonymous.headers["location"] == "/login?next=/accounts"
    assert teacher_client.get("/accounts").status_code == 403
    assert student_client.get("/accounts").status_code == 403


def test_the_add_account_dialog_opens_for_an_admin(accounts_client) -> None:
    fragment = accounts_client.get("/accounts/new", headers=HTMX_HEADERS)
    assert fragment.status_code == 200
    assert 'action="/accounts"' in fragment.text
    assert 'name="username"' in fragment.text
    assert 'type="password"' in fragment.text
    assert "Grace Hopper" in fragment.text

    plain = accounts_client.get("/accounts/new")
    assert plain.status_code == 200
    assert "Add account" in plain.text


def test_an_admin_creates_an_account_over_htmx(accounts_client) -> None:
    response = accounts_client.post(
        "/accounts",
        data={
            "username": "ana.perez",
            "role": "student",
            "student_id": "2",
            "password": PASSWORD,
            "confirm": PASSWORD,
        },
        headers=HTMX_HEADERS,
    )

    assert response.status_code == 200
    assert "ana.perez" in response.text
    account = database.get_user_by_username("ana.perez")
    assert account is not None
    assert account.student_id == 2
    assert database.authenticate("ana.perez", PASSWORD) is not None


def test_an_admin_creates_an_account_without_javascript(accounts_client) -> None:
    response = accounts_client.post(
        "/accounts",
        data={
            "username": "secundario",
            "role": "teacher",
            "password": PASSWORD,
            "confirm": PASSWORD,
        },
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/accounts"
    assert database.get_user_by_username("secundario") is not None


@pytest.mark.parametrize(
    "payload, message",
    [
        (
            {"username": "TEACHER.ONE", "role": "admin", "password": PASSWORD, "confirm": PASSWORD},
            "already taken",
        ),
        (
            {"username": "corta.clave", "role": "admin", "password": "corta12", "confirm": "corta12"},
            "at least 8 characters",
        ),
        (
            {"username": "nuevo.alumno", "role": "student", "password": PASSWORD, "confirm": PASSWORD},
            "must be linked",
        ),
        (
            {"username": "mal.vinculo", "role": "teacher", "student_id": "1",
             "password": PASSWORD, "confirm": PASSWORD},
            "only a student account",
        ),
        (
            {"username": "desigual", "role": "admin", "password": PASSWORD, "confirm": "otra-clave"},
            "do not match",
        ),
        (
            {"username": "a b", "role": "admin", "password": PASSWORD, "confirm": PASSWORD},
            "3 to 32 characters",
        ),
    ],
)
def test_a_rejected_account_is_never_stored(
    accounts_client, payload: dict[str, str], message: str
) -> None:
    before = stored_accounts()

    response = accounts_client.post("/accounts", data=payload, headers=HTMX_HEADERS)

    assert response.status_code == 422
    assert message in response.text
    assert "Traceback" not in response.text
    assert stored_accounts() == before


def test_an_admin_resets_a_password_over_htmx(accounts_client) -> None:
    dialog = accounts_client.get("/accounts/teacher.one/password", headers=HTMX_HEADERS)
    assert dialog.status_code == 200
    assert 'action="/accounts/teacher.one/password"' in dialog.text
    assert "teacher.one" in dialog.text

    response = accounts_client.post(
        "/accounts/teacher.one/password",
        data={"password": "otra-clave-larga", "confirm": "otra-clave-larga"},
        headers=HTMX_HEADERS,
    )

    assert response.status_code == 200
    assert database.authenticate("teacher.one", PASSWORD) is None
    assert database.authenticate("teacher.one", "otra-clave-larga") is not None


def test_an_admin_resets_a_password_without_javascript(accounts_client) -> None:
    response = accounts_client.post(
        "/accounts/admin.one/password",
        data={"password": "otra-clave-larga", "confirm": "otra-clave-larga"},
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/accounts"
    assert database.authenticate("admin.one", "otra-clave-larga") is not None


def test_a_rejected_password_change_changes_nothing(accounts_client) -> None:
    response = accounts_client.post(
        "/accounts/admin.one/password",
        data={"password": "corta12", "confirm": "corta12"},
        headers=HTMX_HEADERS,
    )

    assert response.status_code == 422
    assert "at least 8 characters" in response.text
    assert "Traceback" not in response.text
    assert database.authenticate("admin.one", PASSWORD) is not None


def test_an_unknown_account_answers_not_found(accounts_client) -> None:
    dialog = accounts_client.get("/accounts/nadie/password", headers=HTMX_HEADERS)
    assert dialog.status_code == 404
    assert "not found" in dialog.text.lower()
    plain = accounts_client.get("/accounts/nadie/password")
    assert plain.status_code == 303
    assert plain.headers["location"] == "/accounts"
    posted = accounts_client.post(
        "/accounts/nadie/password",
        data={"password": PASSWORD, "confirm": PASSWORD},
        headers=HTMX_HEADERS,
    )
    assert posted.status_code == 404


def test_a_teacher_cannot_manage_accounts(roster_teacher_client) -> None:
    assert roster_teacher_client.get("/accounts/new").status_code == 403
    assert (
        roster_teacher_client.post(
            "/accounts",
            data={"username": "intruso", "role": "admin",
                  "password": PASSWORD, "confirm": PASSWORD},
        ).status_code
        == 403
    )
    assert roster_teacher_client.get("/accounts/teacher.one/password").status_code == 403
    assert database.get_user_by_username("intruso") is None


# --- Usability round 1 (odd/tasks/role-panels.md L9): reveal passwords, go back ---


def test_every_password_field_offers_a_visibility_toggle(
    anonymous_client, accounts_client
) -> None:
    login = anonymous_client.get("/login")
    assert login.text.count("data-reveal=") == 1

    new_account = accounts_client.get("/accounts/new", headers=HTMX_HEADERS)
    assert new_account.text.count("data-reveal=") == 2

    reset = accounts_client.get("/accounts/admin.one/password", headers=HTMX_HEADERS)
    assert reset.text.count("data-reveal=") == 2


def test_signed_in_pages_link_the_brand_back_to_the_hub(
    teacher_client, admin_client, student_client, anonymous_client
) -> None:
    for page in (
        teacher_client.get("/students"),
        admin_client.get("/accounts"),
        student_client.get("/me"),
    ):
        assert page.status_code == 200
        assert '<a class="brand" href="/"' in page.text

    login = anonymous_client.get("/login")
    assert login.status_code == 200
    assert 'class="brand"' not in login.text
