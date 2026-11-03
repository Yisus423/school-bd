# Vendored browser assets

The web UI loads no external URLs, so these files are committed instead of
fetched from a CDN at runtime. All three projects are MIT licensed.

| File | Package | Version | Source | SHA-256 |
| --- | --- | --- | --- | --- |
| `beer.min.css` | [beercss](https://github.com/beercss/beercss) | 3.12.11 | `https://unpkg.com/beercss@3.12.11/dist/cdn/beer.min.css` | `bd0c3309fdd541e103d605cb0174201fa7b00513d9a2c8aa7d051feb4d9d1f9e` |
| `beer.min.js` | [beercss](https://github.com/beercss/beercss) | 3.12.11 | `https://unpkg.com/beercss@3.12.11/dist/cdn/beer.min.js` | `99b174a78a623f972597a37d6a5fbaae9fe6e6e0eb808f2da7bf1981f15b29d9` |
| `material-dynamic-colors.min.js` | [material-dynamic-colors](https://github.com/leonardorafael/material-dynamic-colors) | 1.2.0 | `https://unpkg.com/material-dynamic-colors@1.2.0/dist/cdn/material-dynamic-colors.min.js` | `89cb765e0f96eefb4a82a412d5b9520228ad69504992221b447b616e0512b446` |
| `htmx.min.js` | [htmx](https://htmx.org) | 2.0.4 | `https://unpkg.com/htmx.org@2.0.4/dist/htmx.min.js` | `e209dda5c8235479f3166defc7750e1dbcd5a5c1808b7792fc2e6733768fb447` |

Notes:

* `beer.min.js` and `material-dynamic-colors.min.js` are ES modules; `app.js`
  imports them, which is what sets `globalThis.materialDynamicColors` before
  `ui("theme", seed)` runs.
* `htmx.min.js` is a classic script and is loaded with `<script defer>`.
* Icons are inline SVG rather than the Material Symbols icon font, so the page
  makes no external font request.
* To update a file, download the pinned version, verify its SHA-256 against this
  table and commit both together.

Verify the checksums with:

```bash
sha256sum static/vendor/*.css static/vendor/*.js
```
