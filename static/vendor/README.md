# Vendored browser assets

The web UI loads no external URLs, so these files are committed instead of
fetched from a CDN at runtime. All three projects are MIT licensed.

| File | Package | Version | Source | SHA-256 |
| --- | --- | --- | --- | --- |
| `beer.min.css` | [beercss](https://github.com/beercss/beercss) | 3.12.11 | `https://unpkg.com/beercss@3.12.11/dist/cdn/beer.min.css` | `3f59689b31d7ac03e1136060bce4d358c130ca58eb14db2e68fdad23774bedec` (trimmed: see below) |
| `beer.min.js` | [beercss](https://github.com/beercss/beercss) | 3.12.11 | `https://unpkg.com/beercss@3.12.11/dist/cdn/beer.min.js` | `99b174a78a623f972597a37d6a5fbaae9fe6e6e0eb808f2da7bf1981f15b29d9` |
| `material-dynamic-colors.min.js` | [material-dynamic-colors](https://github.com/leonardorafael/material-dynamic-colors) | 1.2.0 | `https://unpkg.com/material-dynamic-colors@1.2.0/dist/cdn/material-dynamic-colors.min.js` | `89cb765e0f96eefb4a82a412d5b9520228ad69504992221b447b616e0512b446` |
| `htmx.min.js` | [htmx](https://htmx.org) | 2.0.4 | `https://unpkg.com/htmx.org@2.0.4/dist/htmx.min.js` | `e209dda5c8235479f3166defc7750e1dbcd5a5c1808b7792fc2e6733768fb447` |

Notes:

* `beer.min.js` and `material-dynamic-colors.min.js` are ES modules; `app.js`
  imports them, which is what sets `globalThis.materialDynamicColors` before
  `ui("theme", seed)` runs.
* `htmx.min.js` is a classic script and is loaded with `<script defer>`.
* Icons are inline SVG rather than the Material Symbols icon font, so the page
  makes no font request at all.
* To update a file, download the pinned version, compare its SHA-256 with this
  table and commit both together. `beer.min.css` needs the trim below again.

Verify the checksums with:

```bash
sha256sum static/vendor/*.css static/vendor/*.js
```

## `beer.min.css` is trimmed

As released, `beer.min.css` points at 45 files that are not in this directory: 38
rules that masked an element with one of 37 `*.svg` shape files, and four
`@font-face` blocks for the Material Symbols icon fonts. The app uses no `.shape.*`
class and draws its icons as inline SVG, so the browser asked for all 45 on every
page load and got a `404` for each one. That is 41 pointless requests per page, and
a headless browser needed about 2.1 s to settle an empty page that only linked this
stylesheet, against 0.5 s once the references were gone.

The trim removed exactly two things: the `@font-face` blocks whose family is a
Material Symbols one, and the rules whose body contains a `url()` that does not
resolve. The released file's SHA-256 was
`bd0c3309fdd541e103d605cb0174201fa7b00513d9a2c8aa7d051feb4d9d1f9e`, and it was
89,347 bytes; the trimmed file is 84,789 bytes.

To repeat it after an upgrade, from the repository root:

```python
import re, pathlib
p = pathlib.Path("static/vendor/beer.min.css")
css = p.read_text()
missing = lambda t: [u for u in re.findall(r"url\(\s*([^)'\"]+?)\s*\)", t)
                     if not u.startswith("data:") and not (p.parent / u).exists()]
css = re.sub(r"@font-face\s*\{[^{}]*\}",
             lambda m: "" if "Material Symbols" in m.group(0) else m.group(0), css)
css = re.sub(r"([^{}]+)\{([^{}]*)\}",
             lambda m: "" if missing(m.group(2)) else m.group(0), css)
assert not missing(css), "a url() still points at nothing"
p.write_text(css)
```

If you ever use a `.shape.*` class or the icon font, re-vendor the pristine file and
copy the SVGs or `woff2` files you need from the same pinned release.
