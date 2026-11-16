# web-auth — Login with students, teachers and admins

Phase 3 of school-bd: real accounts and a login on top of the existing web UI, so the
student CRUD stops being public and a student can sign in and see only their own record.
Phase 2 is closed on `master` (`9c4bd48`, merge of `feat/web-student-crud`).

Specification for the design and implementation tasks below. Read until `## Log`.

## Specs

S1. Who can log in — user decision (2026-11-15, question "¿Quiénes van a poder
    loguearse en la web?"): **"Docentes, admin y alumnos"**. Verbatim option text:
    "Tres tipos de usuario; el alumno entra y ve solo lo suyo (base para
    notas/asistencia)."

S2. Who creates accounts — user decision (2026-11-15, question "¿Cómo se crean y
    administran las cuentas?"): **"CLI ahora, panel después"**. Verbatim option text:
    "Se siembran las cuentas por CLI y la gestión web queda como fase siguiente."

S3. Origin of the phase — user decision (2026-11-10): "quede con el profesor de
    agregar un login y tener estudiantes y profesores".

S4. Preserved behavior and contracts (unchanged by this phase): SQLite stays the
    engine at `db.sqlite3` and the `students` table keeps its columns (`id`, `name`,
    `age`, `birthday`, `course`); `models.py` owns the SQLModel tables and Pydantic
    validation; `database.py` owns persistence only; `cli.py` keeps its public
    commands `list`, `add`, `show`, `edit`, `delete` with readable `Error:` messages
    and exit code 1; `web.py` keeps its student routes and their HTMX/non-HTMX
    answers; validation rules stay shared, never duplicated per surface; and the
    phase-2 copy rule still holds — visible text never names files, tools, layers or
    storage (`db.sqlite3`, `models.py`, `web.py`, `CLI`, `API`, `SQLite`).

S5. The login itself — user request (2026-11-15): "haz mem_context y pasemos a hacer
    el login".

S6. Known limitation, stated rather than hidden: the login and logout forms carry no
    CSRF token. Session cookies are `SameSite=Lax`, which keeps a cross-site POST from
    carrying the session cookie, but login CSRF is not defended against. This phase
    does not claim CSRF protection.

## Tasks

- T1 (S1, S2, S3) — Persistence and hashing: `Role` enum, `User` table (username,
  password hash, role, optional link to a student row) and password hashing on the
  Python standard library. Route: inline. Status: done, in W1a.
- T2 (S2, S3) — Account CLI: `users add`, `users list`, `users passwd`, `users
  remove`, with prompts for the password and readable errors. Route: inline.
  Status: done, in W1b.
- T3 (S1, S5) — Server-side sessions: `LoginSession` table holding a hash of the
  cookie token plus its expiry, and the helpers that issue, resolve and revoke them.
  Route: inline. Status: done, in W2.
- T4 (S1, S4, S5) — Web entry and guards: `GET/POST /login`, `POST /logout`, the
  role guard applied to the existing student routes, and `GET /me` for a student.
  Route: inline. Status: done, in W2.
- T5 (S1, S4, S5) — Pages: login form, the student's own record, and a top bar that
  shows who is signed in with a way out. Route: inline. Status: done, in W2.
- T6 (S1–S5) — Tests: one for every rule this phase introduces, one for the student
  behavior the guards touch, and one differential check against the base commit for
  the commands and routes this phase did not name. Route: inline. Status: in
  progress: the account half (`tests/test_auth.py`, the account cases in
  `tests/test_cli.py`) and the differential run for the student commands landed in
  W1a/W1b and reported byte-identical output; the web half landed in W2 (15 rules
  first seen red, then green) with the student-page differential run against the base
  commit.
- T7 (S2, S4) — Documentation: README section for accounts and roles, plus the CLI
  help text that describes what a user can do. Route: inline. Status: done, in W3.
- T8 (S1–S6) — Independent verification of the security surface (Risk item 2) and
  close. Route: `gentle-ai-verify`. Status: pending.

Work units (commits on `feat/web-auth`, about 400 authored lines each):

- W1a — `feat(auth): add users, roles and password hashing` (T1 and
  `tests/test_auth.py`).
- W1b — `feat(cli): manage accounts from the users command group` (T2 and its tests
  in `tests/test_cli.py`). W1a and W1b were originally one slice: it measured 741
  authored lines, so the delivery strategy split it at the layer boundary before
  the next commit (see L6).
- W2 — `feat(web): require a session login and guard the student routes by role`
  (T3, T4, T5, their tests). Split the same way if it passes the slice size.
- W3 — `docs(auth): document accounts, roles and sessions` (T7), then T8.

## Log

L1 (2026-11-15, user, verbatim): "haz mem_context y pasemos a hacer el login"

L2 (2026-11-15, user answers, verbatim): "Docentes, admin y alumnos" and
"CLI ahora, panel después".

L3 (2026-11-15, parent, decision — implementation freedom, not a user requirement):
sessions are server-side rows in SQLite with an opaque `secrets.token_urlsafe` cookie
token stored as its SHA-256 digest, instead of Starlette's `SessionMiddleware`: that
middleware needs `itsdangerous`, which is absent from the venv and from `uv.lock`,
and adding a dependency is a side effect this phase does not need. Passwords are
hashed with `hashlib.scrypt` from the standard library rather than a new dependency.
Both choices are recorded because they are the security-relevant ones.

L4 (2026-11-15, parent, decision): the web admin panel for users stays deferred to a
later phase (S2), and the `/admin` branding screen recorded on 2026-11-10 stays
deferred too. `admin` is a role value this phase can create and log in with; it grants
no power that `teacher` does not already have, and the docs say so instead of
pretending otherwise.

L5 (2026-11-15, parent, decision): this phase implements the login page in the visual
language already shipped in `templates/students.html` (BeerCSS plus `static/app.css`,
the same top bar), because S1 asks for a working login and the project's chosen
direction is already implemented. No new artboards or `design/system.md` sync are
produced for it; the canvas pass stays available on request.

L7 (2026-11-15, parent, decision): a `LoginSession.expires_at` column is an aware UTC
`datetime`, never a naive one: SQLModel maps `datetime` to its `UTCDateTime`, which
raises on a value without a time zone. Two other measurements shaped the tests:
`hashlib.scrypt` at the pinned cost takes about 300 ms on this machine, so the web
fixtures create only the account each test signs in with instead of one per role in
every test; and the whole suite still took 102 tests in 16 s before this phase, so the
suite runtime is reported rather than hidden.

L8 (2026-11-15, parent, decision): the parent context reached its backstop while the
web half was in flight, so the remaining bounded unit — one missing admin test, the
full suite, and the differential run for the student pages — was delegated to a
worker with the file list it may touch, and reported back as evidence.

L6 (2026-11-15, parent, decision): the account work measured 741 authored lines as
one slice, past the review-size target, so it is delivered as two: persistence and
hashing (`feat(auth)`), then the CLI surface that uses them (`feat(cli)`). The
account tests travel with the slice that owns the behavior they describe; the CLI
slice therefore also exercises `database.add_user` and the account schema, through
the CLI rather than through internal storage. Checks run: the full suite (102 passed),
a differential run of `list`, `add`, `show`, `edit`, `delete`, an invalid add, two
missing identifiers and a bad command against a `git archive master` copy (output
identical), and RED for the new rules by running the new test modules in that same
copy, where both fail at import because the account feature does not exist there.
