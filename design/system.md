# School DB — design system

Captured from the project's own sources on 2026-11-16. Only values found in those
sources are recorded. `static/vendor/beer.min.css` is BeerCSS 3.12.11 (Material You),
trimmed per `static/vendor/README.md`; `static/app.css` adds the project's small
layer on top; `templates/` shows how the components are actually used.

## How color works at runtime

The tokens below are the **default palette** BeerCSS ships in `:root`. The app then
overrides them in the browser: `static/app.js` calls `ui("theme", source)` from
`material-dynamic-colors`, deriving the whole Material You palette from the source
configured in `school.toml` (`palette = "logo"` samples the logo image,
`palette = "color"` uses the seed color). A page therefore paints with the tokens
below only until that resolves; every color a design shows should be read as
"derived from the school's seed", not as a fixed brand color.

## Colors

| Token | Value | Usage |
| --- | --- | --- |
| `--primary` | `#6750a4` | Filled buttons, active tab indicator, links, focus. |
| `--on-primary` | `#ffffff` | Text and icons on `--primary`. |
| `--primary-container` | `#e9ddff` | Selected/highlighted fills. |
| `--on-primary-container` | `#22005d` | Text on `--primary-container`. |
| `--secondary-container` | `#e8def8` | Secondary chips and gentle fills. |
| `--on-secondary-container` | `#1e192b` | Text on `--secondary-container`. |
| `--error` | `#ba1a1a` | Destructive actions and field errors. |
| `--on-error` | `#ffffff` | Text on `--error`. |
| `--background` | `#fffbff` | Page background. |
| `--surface` | `#fdf8fd` | Cards, tables, dialogs. |
| `--surface-container` | `#f2ecf1` | Recessed areas behind cards. |
| `--active` | `rgb(128 128 128 / .192)` | Pressed/hover wash. |
| `--overlay` | `rgb(0 0 0 / .5)` | Scrim behind a dialog. |

Dark theme: `body.dark` swaps the same token names (sample: `--primary=#cfbcff`,
`--on-primary=#381e72`, `--primary-container=#4f378a`). The app currently ships no
dark toggle; the page follows BeerCSS defaults only.

## Typography

| Token / rule | Value | Usage |
| --- | --- | --- |
| `--font` | `Inter, Roboto, "Helvetica Neue", "Arial Nova", "Nimbus Sans", Noto Sans, …` (system stack, see source) | Everything. |
| `--size` | `1rem` | Base body size. |
| small text | `.75rem` | Captions, chips, table metadata. |
| secondary text | `.875rem` | Field hints, secondary labels. |
| display | `3.5625rem` | Largest headline scale step declared by BeerCSS. |

## Spacing

| Token / rule | Value | Usage |
| --- | --- | --- |
| `--size` | `1rem` | Base unit for gaps and padding. |
| field height | `3rem` | `.field` components. |
| chip size | `2rem` | `.chip` height. |
| dialog padding | `1.5rem` | Inside `<dialog>`. |
| chip inner padding | `.75rem` | `.chip`. |

## Radius

| Component | Value |
| --- | --- |
| `.chip` | `0.5rem` |
| `.field` (outlined) | `0.25rem 0.25rem 0 0` (top corners only) |
| `dialog` | `1.75rem` |
| app logo | `12px` (rect `rx=12` in `static/logo.svg`) |
| `.skip` focus pill | `0.25rem` (`static/app.css`) |

## Elevation

| Token | Value |
| --- | --- |
| `--elevate1` | `0 .125rem .125rem 0 rgb(0 0 0 / .32)` |
| `--elevate2` | `0 .25rem .5rem 0 rgb(0 0 0 / .4)` — used by `dialog` |
| `--elevate3` | `0 .375rem .75rem 0 rgb(0 0 0 / .48)` |

## Motion

| Token | Value |
| --- | --- |
| `--speed1`…`--speed4` | `.1s`, `.2s`, `.3s`, `.4s` |

`static/app.css` sets `transition: none !important` for everything under
`prefers-reduced-motion: reduce`.

## Component rules (as the app actually renders them)

| Component | Rule | Source |
| --- | --- | --- |
| Top bar | `<header><nav>`: `.circle` logo 40×40, `h5.max` with the school name, `.chip`s for page/identity, transparent `.button` in a form for Sign out. | `templates/students.html:17-24` |
| Toolbar | `form.row` with two outlined `.field`s (search with `placeholder=" "`, course select) and a filled `.button` anchor. Server-side filtering via `q`/`course_filter`. | `templates/students.html:27-46` |
| Table | Inside `article.border.round`; `<caption>` describes it; numeric columns get `class="numeric"` (right-aligned, tabular nums, `app.css`); actions column right-aligned nowrap with inline-SVG icon buttons. | `templates/students.html:48-67`, `static/app.css` |
| Counter | `partials/count.html` renders "N students" in a `<nav>` under the table; HTMX swaps update it out-of-band. | `templates/partials/count.html` |
| Fields | `div.field.label.border.round` wrapping `input` + `label`; labels float; errors render in `dialog > form > .error-container`. | `templates/partials/form.html` |
| Buttons | Filled `.button` for primary actions; `.transparent` inside the top bar for Sign out; destructive delete is a filled button with `--error` styling inside its dialog. | `templates/partials/confirm.html` |
| Dialogs | `<dialog>` (radius `1.75rem`, `--elevate2`), a form with `nav` for actions; HTMX swaps them into `#dialog-host` and `app.js` calls `showModal()`, focusing `[data-autofocus]`. | `static/app.js`, `web.py` |
| Identity | The signed-in account renders as a `.chip` with the username; Sign out is a form POST to `/logout`. | `templates/students.html` (phase web-auth) |
| Skip link | `.skip` off-canvas, becomes a fixed `--primary` pill on focus. | `static/app.css` |

Sources: `static/vendor/beer.min.css`, `static/app.css`, `static/logo.svg`,
`templates/students.html`, `templates/login.html`, `templates/me.html`,
`templates/partials/*.html`.
