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

## Tasks

- T1 (S3) — Design directions for the student admin UI: 3 artboards under
  `design/student-admin/` plus `design.json`. Route: inline. Status: done,
  the docs slice commit (this commit).
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
  the task evidence is recorded here. Route: inline. Status: done, commit
  `0da0c6d` (docs slice).

## Delivery

Strategy: the feature lands as four reviewable commits on the feature branch
`feat/web-student-crud`, branched from `master` per the ODD default-branch rule;
`master` is untouched. Pushing, a pull request and the merge stay with the user.

| Slice | Commit | Content | Authored lines |
| --- | --- | --- | --- |
| Stack + assets | `af31e13` | `pyproject.toml`, `uv.lock`, `static/vendor/` | deps only (high-risk slice, kept alone) |
| App | `771f2b2` | `web.py`, `settings.py`, `school.toml`, `templates/`, `static/app.css`, `static/app.js`, `static/logo.svg` | ~880 |
| Tests | `0df5481` | `tests/test_web.py`, `tests/test_settings.py` | ~520 |
| Docs | this commit | `README.md`, `odd/tasks/`, `design/student-admin/` | ~290 |

The measured total is 1695 authored changed lines, past the ~400-line review
slice, so if this becomes a pull request it must be delivered as chained PRs on
these exact boundaries (stack/assets, app, tests, docs) rather than one review.

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
vendored browser assets)`. Verification: the independent verifier ran over the
diff of `feat/web-student-crud`; its verdict is recorded in the Engram mirror `odd/web-student-crud/tasks` together with the final commit hashes.

L12 (known cosmetic, parent, 2026-11-02): this environment's Starlette emits
`StarletteDeprecationWarning: Using httpx with starlette.testclient is
deprecated; install httpx2 instead` on every test run. The suite passes; the
project keeps `httpx` in the development group and `pyproject.toml` is otherwise
untouched.
