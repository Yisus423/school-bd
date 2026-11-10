# web-student-crud — FastAPI web UI for student CRUD

Phase 2 of school-bd: a server-rendered web application over the existing SQLModel
persistence layer, with BeerCSS styling and HTMX interactions. Phase 1 (the SQLModel
migration) is closed in commit `6550349`.

Specification for the design and implementation tasks below. Read until `## Log`.

## Specs

S1. Web stack: FastAPI serving server-rendered HTML with HTMX partial swaps and
    BeerCSS styling. Recorded user requirement (Engram obs 1277, 2026-10-29):
    "luego empezaremos la web con fastapi,beercss ..." (registered excerpt; the
    phase-1 half of that prompt is already closed by commit `6550349`).

S2. Scope of this phase, user decision (2026-11-02): "CRUD completo de alumnos" —
    "Listar, crear, editar y borrar alumnos desde el navegador, reusando
    database.py". All four operations must work from the browser.

S3. User decision (2026-11-02): "Sí, artboards primero" — "Correr gentle-design con
    BeerCSS y elegir dirección visual antes de tocar FastAPI". No implementation
    task starts before the design directions exist and one is chosen.

S4. User decision (2026-11-02): "Commitear fase 1 como unidad" — the SQLModel
    migration is committed as one unit. DONE: commit `6550349` on `master`.

S5. Preserved behavior and contracts (from phase 1, unchanged by this phase):
    SQLite stays the engine at `db.sqlite3` with the existing `students` table
    (`id`, `name`, `age`, `birthday`, `course`); `models.py` owns the SQLModel tables
    and Pydantic validation; `database.py` owns persistence only; `cli.py` keeps its
    public commands `list`, `add`, `show`, `edit`, `delete` with readable `Error:`
    messages and exit code 1; validation rules (trimmed non-empty name, age
    `1..130`, real `YYYY-MM-DD` birthday) are shared, not duplicated per surface.

S6. The web layer must not mutate stored data on invalid input, and must not
    duplicate persistence logic: every route delegates to `database.py`.

S7. Palette source, user decision (2026-11-02): "aplicas lo del pallete en el
    school.toml". `school.toml` decides where the Material You palette comes from:
    `palette = "logo"` samples the logo image, so changing the logo changes the
    colorscheme, and `palette = "color"` derives it from `SCHOOL_COLOR`. The page
    must survive a failed sampling: it receives the resolved source plus the color
    as a fallback, and the CSS default palette is the last resort. This also
    discharges the canvas comment `2nkbkn3z` (the school's own palette, via Material
    You).

S8. Visible copy, user decision (2026-11-02): "quitemos toda la charla interna
    innecesaria". User-facing text never names files, tools, layers or storage
    (`db.sqlite3`, `models.py`, `web.py`, `CLI`, `API`, `SQLite`); a constraint shows
    up as an input attribute (`min`, `max`, `type`) and as an error only when a value
    is rejected. Explanations for developers live in code comments and docs, never
    on the page.

## Tasks

- T1 (S3) — Design directions for the student admin UI: 3 artboards under
  `design/student-admin/` plus `design.json`. Route: inline. Status: done, docs
  slice `9fb3615`.
- T2 (S1, S5) — FastAPI app plus Jinja2 templates and local static assets
  (BeerCSS served from `static/vendor/`, no CDN). Route: inline. Status: done,
  commits `af31e13` (stack and vendored assets) and `771f2b2` (app).
- T3 (S2, S6) — Read surface: student list with server-side search and course
  filter. Route: inline. Status: done, commit `771f2b2`.
- T4 (S2, S6) — Create surface: add-student dialog, HTMX submit, validation errors
  rendered in-page without writing data. Route: inline. Status: done, commit
  `771f2b2`.
- T5 (S2, S6) — Edit surface: prefilled update dialog for one student. Route:
  inline. Status: done, commit `771f2b2`.
- T6 (S2, S6) — Delete surface: confirmation dialog before deletion. Route:
  inline. Status: done, commit `771f2b2`.
- T7 (S2, S5, S6) — Tests: FastAPI `TestClient` coverage of the four operations
  against isolated temporary databases, including invalid input leaving data
  unchanged, plus one CLI regression test. Route: delegated
  (`gentle-ai-worker`, task `mw07ng7e-1-6ih9`). Status: done, commit `0df5481`.
- T8 (S5) — Docs: README gains the web phase (setup, run, routes, branding) and
  the task evidence is recorded here. Route: inline. Status: done, docs slice
  `9fb3615`.
- T9 (S7) — Palette source in `school.toml` (`logo` or `color`) with its fallback
  chain and tests. Route: inline. Status: done, commit `5a8c3d3`.
- T10 (S8) — Remove the internal talk from the rendered page and dialogs. Route:
  inline. Status: done, commit `5a8c3d3`.

## Delivery

Strategy: the feature lands as reviewable commits on the feature branch
`feat/web-student-crud`, branched from `master` per the ODD default-branch rule;
`master` is untouched. Pushing, a pull request and the merge stay with the user.

| Slice | Commit | Content | Authored lines |
| --- | --- | --- | --- |
| Stack + assets | `af31e13` | `pyproject.toml`, `uv.lock`, `static/vendor/` | deps only (high-risk slice, kept alone) |
| App | `771f2b2` | `web.py`, `settings.py`, `school.toml`, `templates/`, `static/app.css`, `static/app.js`, `static/logo.svg` | ~880 |
| Tests | `0df5481` | `tests/test_web.py`, `tests/test_settings.py` | ~520 |
| Docs | `9fb3615` | `README.md`, `odd/tasks/`, `design/student-admin/` | ~290 |
| Fix | `f572177` | `web.py`, `tests/test_web.py` | ~45 |
| Branding + copy | `5a8c3d3` | `settings.py`, `school.toml`, `static/app.js`, `static/logo.svg`, `templates/`, tests, `README.md` | ~90 |

Outcome: the user validated the app in class and then asked to merge, so the feature was
merged into `master` with `--no-ff` as `9c4bd48` (29 files, 3587 insertions, 12 deletions)
and `uv run pytest -q` reports 74 passed on the merged `master`. No push was performed:
publishing stays with the user. Note the remote state at merge time: the branch
`feat/web-student-crud` is already on `origin` at `efcf959`, while `origin/master` is
still at `bb36ae1`, so phase 1 (`6550349`) and this feature are not published on the
default branch yet. The branch is kept locally and remotely.

Accounting note (parent): the raw count runs to 3393 authored lines because the
three artboards under `design/student-admin/` are ~2000 lines of self-contained
alternative HTML whose purpose is to be compared, not shipped; the product code
is the stack/assets, app, tests, fix and docs slices above. Either way the total
is past the ~400-line review slice, so if this becomes a pull request it must be
delivered as chained PRs on these exact boundaries (stack/assets, app, tests,
fix, docs) rather than one review.

The `## Log` endpoint differs from the task commits in one respect: the artboards
were revised once, in the last docs commit, so that the chosen direction shows the
resolved branding comments (the logo slot and the note that name, logo and seed
colour come from `school.toml`).

## Log

L1 (user, 2026-11-02, verbatim): "arranquemos con la s8guiente fase"

L2 (user, 2026-10-29, Engram obs 1277, verbatim): "Me gustaría pasar este proyecto
de sqlite a sqlmodel para eliminar al mismo tiempo todas esas funciones de
verificación o modificarlas para usar pydantic, luego empezaremos la web con
fastapi,beercss ..." — phase 1 closed in `6550349`; this document tracks the
"web con fastapi,beercss" half.

L3 (user decisions, 2026-11-02, one batch): (a) base = "Commitear fase 1 como
unidad"; (b) scope = "CRUD completo de alumnos"; (c) design = "Sí, artboards
primero"; (d) RDD = "rdd ya está apagado".

L4 (decision, parent, 2026-11-02): phase-1 review lineage `review-62404378172c9e6e`
stays dormant and untouched (1 of 4 lenses captured, 3 slots re-offered). Reported
to the user; not resumed without a new instruction. `gentle-ai review mode status`
still reports RDD `on (decided by global)` while the user states it is off; the
switch is human-owned and `--scope clone` is unset, so no native review runs in this
phase without an explicit new user decision.

L5 (evidence, parent, 2026-11-02): baseline before this phase — `uv run pytest -q`
→ `32 passed in 1.33s`; `git status --short` → clean after `6550349`.

L6 (decision, parent, 2026-11-02): UI copy, template names, docstrings and commit
messages in English, matching the existing project convention (`README.md`, `cli.py`
messages). Artboards follow the gentle-design hard rules: self-contained HTML, inline
CSS/JS/SVG, no external URLs or CDNs, system font stacks.

L7 (evidence, parent, 2026-11-02): gentle-design gate ran — `gentle_design(list)`:
no designs, no system board, `Design sources: none detected`, so no design-system
sync was needed and the artboards are designed freely.

L8 (design, parent, 2026-11-02): `design/student-admin/` created for T1 — three directions as
self-contained artboards, all alternatives, none handed off yet:
`01-dense-table.html` (dense admin table), `02-card-grid.html` (student cards grid),
`03-master-detail.html` (master-detail split), with `design/student-admin/design.json`
(`feature: odd/tasks/web-student-crud.md`). Checks run: `design.json` parses;
`grep -nE "https?://|//cdn|unpkg|jsdelivr"` over the artboards and the manifest → no external
references; tag-balance check per file → no unclosed or stray non-void elements.
Canvas opened at `http://127.0.0.1:40157/-2J8VnK0KKHSjkRVDrDTKiAap3gp18Rc/d/student-admin/`.

L9 (user + design, 2026-11-02): the user chose the dense admin table direction
(`01-dense-table.html`) on the canvas. That handoff also carried two canvas
comments, both applied in the implementation and resolved afterwards:
`2nkbkn3z` (configurable school name and logo, with the BeerCSS Material You
palette derived from the school color) and `xc8v0dfa` (the school logo belongs in
the app bar). Consequence: `settings.py`, `school.toml` and the `SCHOOL_*`
overrides were added to the phase, and the app bar renders the configured logo.
The other two artboards stay as alternatives; they are not implemented.

L10 (implementation evidence, parent, 2026-11-02):

* Manual smoke run against a temporary SQLite engine (parent, inline): 30 checks
  covering `GET /` redirect, page render with seeded rows, no external URL in the
  markup, root-relative static paths, server-side filtering, HTMX row fragment
  with the out-of-band counter, create/update/delete over HTMX with
  `HX-Trigger`, 404 fragments for missing students, four rejected-input cases
  with the stored rows unchanged, `303` Post/Redirect/Get without HTMX, `422`
  full page with the dialog open, and all six static assets at `200`.
* Delegated suite (T7, `gentle-ai-worker` task `mw07ng7e-1-6ih9`): RED/GREEN not
  active (the app already existed), and the run reported `63 passed` after the
  parent fixed the defect below.
* Parent check that the delegated tests are not vacuous (mutation run in a
  `mktemp -d` scratch copy, never committed): removing the `HX-Trigger` header
  failed 3 tests; forcing `422` to `200` and disabling the logo validator failed
  11 tests.
* Two parent defects were found by the smoke run and fixed before the commits:
  `url_for('static', ...)` rendered absolute URLs (now root-relative, which also
  keeps proxies and the offline rule honest), and plain form posts rendered the
  page instead of issuing the `303` redirect. A third defect was in the template
  contract: `dialog.values` resolved to the dict method in Jinja, so the edit
  dialog rendered empty fields; the key is now `fields`.
* Delegated tests surfaced one application defect: `_SAFE_LOGO` allowed the path
  segment `..`, so `logo = "../secret.png"` was accepted. Fixed in `settings.py`
  by rejecting `//`, `.` and `..` segments; both logo-escape cases now raise
  `pydantic.ValidationError`.

L11 (risk, parent, 2026-11-02): `Risk: item 2 (a user-configurable path is
interpolated into a URL: the logo validator is the only guard, and the delegated
test found it permissive) and item 5 (four new runtime dependencies and four
vendored browser assets)`. Verification: see L14 — the independent verifier
returned no verdict, so the checks behind this line are the parent-run ones plus
the adversarial matrix, and the remaining proof gap is recorded there.

L12 (known cosmetic, parent, 2026-11-02): this environment's Starlette emits
`StarletteDeprecationWarning: Using httpx with starlette.testclient is
deprecated; install httpx2 instead` on every test run. The suite passes; the
project keeps `httpx` in the development group and `pyproject.toml` is otherwise
untouched.

L13 (defect found and fixed, parent, 2026-11-02): the parent adversarial pass
found that `GET /students/99999999999999999999/edit` answered `500`:
`database.get_student` raised `OverflowError: Python int too large to convert to
SQLite INTEGER` inside the driver. Fixed in commit `f572177` with
`web.py:is_stored_id`, a guard on the positive signed 64-bit range applied to
every route that takes a student id, plus three tests in `tests/test_web.py`.
Out-of-range identifiers now follow the missing-student contract (`404` fragment
for HTMX, `303` otherwise) and writes return before any database call. The same
`OverflowError` exists in the CLI (`uv run python cli.py show
99999999999999999999` prints a traceback); that is pre-existing phase-1 behaviour,
is NOT changed here, and stays as an open follow-up for the user.

L14 (verification status, parent, 2026-11-02): the independent verifier
(`gentle-ai-verify`, task `mw0ff7f6-2-nz09`) returned NO verdict: it stalled and
timed out with a harness error (`Extension package "builtin:codemode" ...
registers tool codemode, so built-in extension codemode was not loaded`). It was
not retried. What the parent ran instead, labelled as parent-run and not as
independent verification: `uv run pytest -q` -> 70 passed; a mutation run in a
`mktemp -d` scratch copy (dropping `HX-Trigger` failed 3 tests, forcing `422` to
`200` and disabling the logo validator failed 11); `sha256sum` over the four
vendored files against the table in `static/vendor/README.md` -> all four match;
`uv lock --check` -> resolved 34 packages; `grep` for external references across
`templates/`, `static/app.css` and `static/app.js` -> none; a branding matrix
(12 rejected logo values including `../secret.png`, `/etc/passwd`, `a/./b.png`,
`a//b.png`, `logo.svg?x=1`, `logo.svg/`, backslashes and percent-encoding; 3
accepted) and an input matrix (age `130` accepted, `0`/`131`/`abc`/empty/`3.5`
rejected, four birthday forms, markup in `name` and in `q` escaped in the
rendered HTML). Open proof gap: no independent pass over the two high-risk items.

L15 (user correction, 2026-11-02, verbatim): "Podríamos quitar ese 1 to 130 del dialogo
(es solo verificación interna, al usuario ni le importa hasta que lo pone) y el formato
yyyy-mm-dd (el navegador te abre el calendario)." Applied in the follow-up slice
`refactor(web): drop the static field hints from the student dialog`:
`templates/partials/form.html` no longer renders the two `<span class="helper">`
texts. The `min="1" max="130"` attributes and `type="date"` stay (they are the
mechanical constraints and the browser calendar), and the field errors still appear
on rejection. Server-side validation rules are unchanged: the API and the CLI still
require an age of `1..130` and a real `YYYY-MM-DD` birthday.

L16 (user correction, 2026-11-02, verbatim): "htmx lo elegí yo, ya sabía que era de los
mejores para paginas 'semi-estaticas'." Correction to L9's framing: the HTMX choice is
the user's own, not an inheritance from the previous session's plan. The stack in S1
stands as confirmed by the user.

L17 (user, 2026-11-02, verbatim, deferred): "Este es un proyecto para un curso y me
gustaría demostrar capaz un setup on /admin dobde pueda cambiar el logo y cambie todo el
colorscheme, pero eso queda para después." Recorded as a FUTURE phase, not started.
Its implications, for whoever picks it up: an `/admin` route that mutates branding needs
authentication (the app has none today); `settings.py` currently loads `school.toml`
through `lru_cache` at process start, so a write path needs atomic file replacement or a
`settings` table plus cache invalidation; a logo upload is a file-write surface and must
be validated and confined to `static/` like `SchoolSettings.logo` already is; and the
palette can then be derived from the uploaded logo image instead of the seed color
(`ui("theme", "/static/<logo>")`). Design it as its own ODD feature document when the
user green-lights it.

L18 (user, 2026-11-02, verbatim): "Primero quitemos toda la charla interna
innecesaria, aplicas lo del pallete en el school.toml y ya de ahí lo próximo sería
hacer un login o la base de los tres tipos de usuario (student, teacher y admin)".
Both authorized items are done in commit `5a8c3d3` (specs S7 and S8). Evidence:
`uv run pytest -q` -> 74 passed, and the rendered page, the add/edit dialog and the
delete confirmation contain none of `db.sqlite3`, `models.py`, `web.py`, `CLI`,
`API`, `SQLite`, `Validated by` or `record from the database`.

L20 (user, 2026-11-02, verbatim): "lo probe en el curso y funciono, mergea y pasamos en
la siguiente sesion a lo siguiente, quede con el profesor de agregar un login y tener
estudiantes y profesores". Two things came in this entry: field validation (the user ran
the app in class, which is the strongest evidence this phase has) and explicit merge
authorization. Merged as `9c4bd48`; no push (publishing is the user's call). Scope
correction for the next phase: L19 quoted "student, teacher y admin", while this entry
says "un login y tener estudiantes y profesores" — the admin role is no longer mentioned
and must be confirmed when that phase starts.

L19 (user, 2026-11-02, verbatim, NEXT PHASE — not started): "lo próximo sería hacer
un login o la base de los tres tipos de usuario (student, teacher y admin)". Read as
the next phase, not as part of this one: the parent asked which of the two comes
first (a login, or the three-role data model) before touching anything. Decisions
that phase must settle: password hashing, session or cookie strategy, and the
permission matrix each role gets over students, courses and branding.
