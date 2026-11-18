# role-panels — One panel per role, accounts from the web, admin branding

Phase 4 of school-bd, built on the login phase (`feat/web-auth`, unmerged). The login
stays as it is; this phase gives each role its own place and moves two management jobs
into the web: creating accounts and changing the school branding.

Specification for the design and implementation tasks below. Read until `## Log`.

## Specs

S1. One panel per role — user decision (2026-11-16, question "¿Qué ve cada rol cuando
    entra?"): **"Admin cuentas; docente alumnos"**. Verbatim option text: "Docente: el
    CRUD de alumnos. Admin: gestión de cuentas. Alumno: su ficha."

S2. Account management from the page — user decision (2026-11-16, question "¿Qué se
    puede hacer con una cuenta desde la página?"): **"Crear y resetear"**. Verbatim
    option text: "Alta y contraseña nueva; la baja sigue siendo por CLI."

S3. Branding in the admin panel — user decision (2026-11-16, question "¿El panel para
    cambiar logo y colores entra en esta fase?"): **"Sí, en el panel del admin"**.
    Verbatim option text: "El admin cambia logo y color desde la web y se rehace la
    paleta."

S4. Design gate — user decision (2026-11-16, question "¿Pasamos por el canvas de
    diseño antes de implementar los paneles?"): **"Sí, artboards primero"**. Verbatim
    option text: "Como la fase 2: direcciones visuales, elegís una, y recién ahí toco
    código." No implementation task starts before one artboard is chosen.

S5. Origin — user request (2026-11-16, verbatim): "debríamos hacer que cada usuario
    tenga un panel distinto y que se puedan crear cuentas desde la pagina". Context of
    the request (verbatim): "el logo si se pinta, capaz es eso una señal de que la
    pagina si esta cargando rapido pero no se esta mostrando rapido."

S6. Preserved behavior (unchanged by this phase): the login phase as shipped on
    `feat/web-auth` — scrypt credentials, server-side sessions, `/login`, `/logout`,
    `GET /me`, and the guards on the student routes; the student CRUD behavior and its
    HTTP contract; the CLI surface, including `users remove`, which stays the only way
    to delete an account (S2); `school.toml` and the `SCHOOL_*` environment variables
    keep working as the base of the branding configuration; the visible-copy rule
    (pages never name files, tools, layers or storage); and `Role.admin` now gains its
    real power, which L4 of `web-auth.md` had explicitly deferred.

S7. Boundaries between roles: a teacher gets `403` on the accounts and branding
    surfaces, exactly as a student does today on `/students`; a student sees no link
    to either; an admin keeps full access to the student CRUD. No role sees another
    role's data.

## Tasks

- T1 (S1–S5, S4 first) — Design directions: sync the project design system
  (`design/system.md`, `design/system.html` — it did not exist and the canvas
  requires it), then three artboards under `design/role-panels/` showing the three
  role experiences, plus `design.json`. Route: inline (a writer stalled twice on
  this unit; see L5). Status: done. Chosen artboard: `03-role-hub.html` (L6).
- T2 (S1, S2, S7) — Admin accounts panel: list accounts, create one (role, username,
  password, student link), reset a password. Route: inline. Status: done (16 tests;
  removal stays CLI-only per S2).
- T3 (S1, S3, S7) — Admin branding panel: change the logo and the seed color from the
  page, with the palette re-deriving; persistence and its precedence over
  `school.toml`/env are an implementation decision to record in `## Log` when made.
  Route: pending, after T1.
- T4 (S1, S7) — Role separation in the shell: the signed-in top bar becomes the
  per-role navigation (admin: students, accounts, branding; teacher: students;
  student: own record), and the guards follow. Route: inline (a writer died at
  rate limit after doing most of the work; see L7). Status: done.
- T5 (S1–S7) — Tests: one RED test per new rule before its implementation, the
  existing behavior each change touches pinned, and a differential check against the
  parent branch for surfaces this phase does not name. Route: pending.
- T6 (S1–S7) — Documentation: README sections for the panels, the accounts screen and
  the branding screen. Route: pending.
- T7 (S1–S7) — Independent verification of the new management surfaces (Risk items 1
  and 2: settings persistence and account creation from the web), or the recorded
  decision not to run it. Route: `gentle-ai-verify`. Status: pending, same open
  question as the login phase's verification.

## Log

L1 (2026-11-16, user, verbatim): "el logo si se pinta, capaz es eso una señal de que
la pagina si esta cargando rapido pero no se esta mostrando rapido. debríamos hacer
que cada usuario tenga un panel distinto y que se puedan crear cuentas desde la
pagina"

L2 (2026-11-16, user answers, verbatim): "Admin cuentas; docente alumnos" ·
"Crear y resetear" · "Sí, en el panel del admin" · "Sí, artboards primero".

L3 (2026-11-16, parent, finding, closing L1's hypothesis): the paint hypothesis was
checked against the running app before opening this phase. The server answers in
7–8 ms, the render-blocking stylesheet arrives in ~19 ms, and a page now issues 8
requests with no 404 left; the only thing that can delay a first paint on loopback is
the browser's own parse-and-paint of ~85 KB of CSS, which no code change of this
project can shave further without dropping BeerCSS. obscura does not expose paint
timings, and it does not draw images in screenshots (the user confirmed the logo
paints in a real browser), so the client-side side rests on those numbers plus the
user's own observation. Nothing more to optimize in this phase.

L4 (2026-11-16, parent, decision): this phase starts on a branch of its own,
`feat/role-panels`, cut from `feat/web-auth` at `1be951e`, so each phase can be
reviewed and merged separately. The login phase's independent verification (T8 of
`web-auth.md`) stays un-run at the user's move-on; it is inherited as T7 here rather
than silently closed.

L9 (2026-11-16, user, verbatim, with screenshots of the hub and the record page):
"esto se ve horrible [Image#1] [Image#2] los cards no se parecen nada a lo que me
enseñaste en el design, lo mismo con el del student [Image#3], y dos mejoras de UX,
tener el botoncito con el ojo para que el usuario pueda ver su contraseña y un boton
para que el usuario pueda regresarse a la pagina anterior (en el caso del teacher y
admin con sus menus para regresar a los cards)".

L10 (2026-11-16, parent, finding): the hub source renders as designed — a re-serve
measured the card at 320 px, the icon at 32 px, the card title at 16.8 px — so the broken
cards in the screenshot were the browser painting a stale `app.css` from cache, not
the template or the stylesheet. The fix is structural rather than a cache-busting
instruction: every asset URL now carries `?v=<sha256 prefix of the file>` computed at
render time, so a changed stylesheet can never be served under an old URL again. The
record page really was wrong as photographed ("Age" floated to the far edge) because
the global full-width `table` rule applied to it; it now uses a compact record table.
Both UX requests in L9 are implemented: an eye button on all five password fields
(login, account create, password reset), and the school name in the top bar is a link
back to the role hub for every signed-in role, which is the way back to the cards.

L8 (2026-11-16, parent, decision): account validation keeps one authority. The web
routes never re-validate an account: they call `database.add_user` and
`set_user_password`, and only route each rejection to the form field that must show
it (a model-level message containing "student record" lands on the student field,
"password" on the password field, anything else on the username). The student-record
select is toggled by a small inline script inside the dialog, so the form works with
and without HTMX; server-side validation does not depend on the toggle. Account
writes report `data-changed` (students keep `student-changed`) and `app.js` closes
the open dialog for either.

L7 (2026-11-16, parent, decision): the T4 writer reached rate limit mid-task after
writing most of the unit; the parent inspected its full diff, replayed the RED it had
not reported (four new/rewritten tests fail against the pre-hub source with the test
changes alone, then pass with the implementation), and committed the unit. Canvas
comment `j9bxvk62` is implemented in the same unit: the account name in every top bar
is a plain label (`partials/identity.html`), and the comment is resolved on the
canvas.

L6 (2026-11-16, user, via the design canvas and the choice prompt): chose
**`design/role-panels/03-role-hub.html`** as the direction for this phase; the
top-tabs and side-rail artboards stay as alternatives. The S4 gate is passed and
implementation tasks may start. With the handoff came canvas comment `j9bxvk62`: the
username next to Sign out looks clickable. Decision: it renders as a plain label, not
a chip — the details of an account live in the admin's accounts panel (T2), and no
self-details page is added. The comment is resolved on the canvas when that lands in
the templates.

L5 (2026-11-16, parent, decision): T1 was routed to a writer twice and both launches
died at startup with harness-level errors (an extension conflict and a missing
provider key in the worker's own environment; one earlier worker task on the perf
unit did complete, so the failure is intermittent but this unit lost the coin toss
three ways with the verify agent). The unit ran inline instead: the design system
was captured by script extraction from `beer.min.css` and the app's own templates,
and the three artboards were written by hand. Same content, different route.
