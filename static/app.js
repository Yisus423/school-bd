// BeerCSS theming plus the small amount of glue HTMX needs for dialogs.
//
// The palette comes from the source configured in school.toml: the logo image
// (`palette = "logo"`) or the school color (`palette = "color"`). BeerCSS derives
// the whole Material You palette from that single source. If the logo cannot be
// read, the school color is tried next; if that fails too, the default palette in
// app.css stays in place.

import ui from "./vendor/beer.min.js";
import "./vendor/material-dynamic-colors.min.js";

const { themeSource, themeFallback } = document.body.dataset;

async function applyTheme(source) {
  if (!source) return false;
  try {
    await ui("theme", source);
    return true;
  } catch (error) {
    console.warn(`Could not derive the palette from ${source}:`, error);
    return false;
  }
}

if (!(await applyTheme(themeSource)) && themeFallback !== themeSource) {
  await applyTheme(themeFallback);
}

// A swapped dialog fragment has to be opened explicitly.
document.body.addEventListener("htmx:afterSwap", (event) => {
  const dialog = event.detail.target.querySelector?.("dialog");
  if (!dialog || dialog.open) return;
  dialog.showModal();
  const focusTarget =
    dialog.querySelector("[data-autofocus]") ?? dialog.querySelector("input, select, button");
  focusTarget?.focus();
});

// `data-close` buttons close their dialog without submitting the form.
document.body.addEventListener("click", (event) => {
  const button = event.target.closest("[data-close]");
  if (button) button.closest("dialog")?.close();
});

// A successful create, update or delete reports `student-changed`.
document.body.addEventListener("student-changed", () => {
  document.querySelectorAll("dialog[open]").forEach((dialog) => dialog.close());
  const host = document.getElementById("dialog-host");
  if (host) host.innerHTML = "";
});
