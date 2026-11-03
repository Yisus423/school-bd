// BeerCSS theming plus the small amount of glue HTMX needs for dialogs.
//
// The dynamic theme comes from the school color in school.toml: BeerCSS derives
// the whole Material You palette from that single seed.

import ui from "./vendor/beer.min.js";
import "./vendor/material-dynamic-colors.min.js";

const seed = document.body.dataset.schoolColor;
if (seed) {
  try {
    await ui("theme", seed);
  } catch (error) {
    console.warn("Could not apply the school color palette:", error);
  }
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
