JSON.stringify((function () {
  var fields = [...document.querySelectorAll(".field")];
  var invalid = document.querySelectorAll(".invalid, .error").length;

  // Every eye button must sit inside the box of its own password field.
  var offscreen = [];
  for (const button of document.querySelectorAll("button.reveal")) {
    const input = document.getElementById(button.getAttribute("data-reveal"));
    if (!input) { offscreen.push(button.getAttribute("data-reveal") + ": missing input"); continue; }
    const b = button.getBoundingClientRect();
    const i = input.getBoundingClientRect();
    if (b.width === 0 || b.left < i.left || b.right > i.right + 1) {
      offscreen.push(button.getAttribute("data-reveal") + ": " + Math.round(b.left) + "-" + Math.round(b.right) + " vs " + Math.round(i.left) + "-" + Math.round(i.right));
    }
  }

  // The palette must have been derived from the seed, and the submit button must
  // wear it. Reading --primary alone cannot prove this: BeerCSS ships a default
  // #6750a4, so the check proves the seed ACTUALLY reached the document first.
  var root = getComputedStyle(document.documentElement);
  var primary = root.getPropertyValue("--primary").trim();
  var body = document.body;
  var seed = (body.dataset.themeSource || "").trim();
  var fallback = (body.dataset.themeFallback || "").trim();
  var derived = /^#([0-9a-f]{3}|[0-9a-f]{6})$/i.test(seed) || /^#([0-9a-f]{3}|[0-9a-f]{6})$/i.test(fallback);
  var submit = document.querySelector('#branding button[type="submit"]');
  var submitBg = submit ? getComputedStyle(submit).backgroundColor : "";

  return {
    fields: fields.length,
    invalid: invalid,
    seed: seed,
    primary: primary,
    submit_bg: submitBg,
    // #6750a4 is the palette BeerCSS ships unpainted. A button still wearing it
    // means the seed never reached the page.
    button_derived:
      derived && submitBg !== "" && submitBg !== "rgba(0, 0, 0, 0)" &&
      submitBg !== "rgb(103, 80, 164)",
    reveal_offscreen: offscreen
  };
})())
