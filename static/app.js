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

// BeerCSS floats a field's label onto the input border only while that input is
// empty (`label.active`, or `:focus + label`). Its empty-state selector needs a
// placeholder that is not whitespace-only, and a real placeholder would print its
// own text inside a password field, so the label carries `active` itself
// whenever the control holds a value, typed or refilled by the browser.
function syncFloatingLabel(control) {
  const field = control.closest(".field");
  const label = field?.querySelector(":scope > label");
  if (!label) return;
  label.classList.toggle("active", control.value !== "");
}

for (const control of document.querySelectorAll(
  ".field > input, .field > textarea, .field > select",
)) {
  syncFloatingLabel(control);
  control.addEventListener("input", () => syncFloatingLabel(control));
  control.addEventListener("change", () => syncFloatingLabel(control));
}

// `data-reveal` buttons toggle the matching password field between hidden and
// shown. The icon swap is pure CSS on aria-pressed, so this only flips state.
document.body.addEventListener("click", (event) => {
  const button = event.target.closest("[data-reveal]");
  if (!button) return;
  const input = document.getElementById(button.getAttribute("data-reveal"));
  if (!input) return;
  const show = input.type === "password";
  input.type = show ? "text" : "password";
  button.setAttribute("aria-pressed", String(show));
  button.setAttribute("aria-label", show ? "Hide password" : "Show password");
  button.setAttribute("title", show ? "Hide password" : "Show password");
});

// A successful write reports `student-changed` (students) or `data-changed`
// (accounts and the screens that follow); either closes the open dialog.
const clearDialogs = () => {
  document.querySelectorAll("dialog[open]").forEach((dialog) => dialog.close());
  const host = document.getElementById("dialog-host");
  if (host) host.innerHTML = "";
};
document.body.addEventListener("student-changed", clearDialogs);
document.body.addEventListener("data-changed", clearDialogs);
