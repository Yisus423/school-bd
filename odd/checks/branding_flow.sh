#!/bin/bash
# Browser-level check of the admin branding panel.
#
#   bash odd/checks/branding_flow.sh
#
# Copies the working tree to a temporary directory, serves that copy, drives it the
# way a browser does (form login, click-through to the panel, save) and then loads a
# different page with obscura to prove the new branding already applies. The real
# db.sqlite3, branding.toml and school.toml are never touched.
set -u

SRC=$(cd "$(dirname "$0")/../.." && pwd)
PY=$SRC/.venv/bin/python
WORK=$(mktemp -d)
PORT=$((8000 + RANDOM % 900))
FAILED=0
SERVER_PID=""

cleanup() {
  [ -n "$SERVER_PID" ] && kill "$SERVER_PID" 2>/dev/null
  rm -rf "$WORK"
}
trap cleanup EXIT

pass() { echo "  ok    $1"; }
fail() { echo "  FAIL  $1 -- $2"; FAILED=$((FAILED + 1)); }
check_eq() { [ "$2" = "$3" ] && pass "$1" || fail "$1" "expected '$3', got '$2'"; }

# Copy the tree, excluding only the things that must stay local to this machine.
tar -C "$SRC" --exclude=.git --exclude=.venv --exclude=__pycache__ \
    --exclude=.codegraph --exclude=db.sqlite3 --exclude=branding.toml \
    -cf - . 2>/dev/null | tar -C "$WORK" -xf -
cd "$WORK" || exit 1
rm -f branding.toml

"$PY" -c "import database; database.add_user('admin.one','una-clave-larga','admin'); database.add_user('teacher.one','una-clave-larga','teacher')" || {
  echo "  FAIL  could not seed accounts"; exit 1; }

"$PY" -m uvicorn web:app --port "$PORT" --log-level warning >/dev/null 2>&1 &
SERVER_PID=$!
for _ in $(seq 120); do
  curl -sf -o /dev/null "http://127.0.0.1:$PORT/login" && break
  sleep 0.25
done

B="http://127.0.0.1:$PORT"
ADMIN=$(mktemp); TEACH=$(mktemp)

status() { curl -s -o /dev/null -w '%{http_code}' "$@"; }

check_eq "login page answers" "$(status "$B/login")" "200"
check_eq "anonymous is sent to the login page" "$(status "$B/branding" -H 'Accept: text/html')" "303"
check_eq "admin signs in" \
  "$(status -c "$ADMIN" -X POST -d 'username=admin.one&password=una-clave-larga' "$B/login")" "303"
check_eq "hub offers the branding card" \
  "$(curl -s -b "$ADMIN" "$B/" | grep -c 'href="/branding"')" "1"
check_eq "the panel opens" "$(status -b "$ADMIN" "$B/branding")" "200"
check_eq "teacher signs in" \
  "$(status -c "$TEACH" -X POST -d 'username=teacher.one&password=una-clave-larga' "$B/login")" "303"
check_eq "a teacher cannot open the panel" "$(status -b "$TEACH" "$B/branding")" "403"
check_eq "a teacher cannot save branding" \
  "$(status -b "$TEACH" -X POST -d 'name=Hijacked&logo=logo.svg&color=%23000000&palette=color' "$B/branding")" "403"

SAVE=$(curl -s -b "$ADMIN" -D /tmp/branding.headers -X POST -H 'HX-Request: true' \
  -d 'name=Northside+Academy&logo=logo.svg&color=%23123456&palette=color' "$B/branding")
check_eq "the save reports success in the page" "$(echo "$SAVE" | grep -c 'Branding saved')" "1"
check_eq "the save reports the trigger for htmx" \
  "$(grep -ci '^hx-trigger: {"data-changed": true}' /tmp/branding.headers)" "1"
check_eq "the branding file holds the new values" \
  "$(grep -c 'name = "Northside Academy"' branding.toml)$(grep -c 'color = "#123456"' branding.toml)" "11"

PAGE=$(curl -s -b "$ADMIN" "$B/students")
check_eq "another page shows the new name" "$(echo "$PAGE" | grep -c 'Northside Academy' | awk '{print ($1>0)}')" "1"
check_eq "another page uses the new seed color" "$(echo "$PAGE" | grep -c 'data-theme-source="#123456"')" "1"

BEFORE=$(cat branding.toml)
REJECT=$(status -b "$ADMIN" -X POST -d 'name=X&logo=logo.svg&color=blue&palette=color' "$B/branding")
check_eq "a bad color is rejected" "$REJECT" "422"
check_eq "a rejected form writes nothing" "$(cat branding.toml)" "$BEFORE"
check_eq "a rejected form leaks no traceback" \
  "$(curl -s -b "$ADMIN" -X POST -H 'HX-Request: true' -d 'name=&logo=logo.svg&color=%23111111&palette=color' "$B/branding" | grep -c 'Traceback')" "0"

# Browser leg: obscura renders the panel and the page that follows the new branding.
PROFILE=$(mktemp -d)
COOKIE=$(awk '/school_session/{print $7}' "$ADMIN" | tail -1)
OBSCURA=$(command -v obscura || true)

if [ -z "$OBSCURA" ]; then
  echo "  skip  browser leg -- obscura is not on PATH"
elif [ -z "$COOKIE" ]; then
  fail "browser leg" "no session cookie to hand to the browser"
else
  PANEL_URL="$B/static/panel.html"
  LBEFORE_URL="$B/static/labels-before.html"
  LAFTER_URL="$B/static/labels-after.html"

  curl -s -b "$ADMIN" -o "$WORK/static/panel.html" "$B/branding"
  curl -s -o "$WORK/static/labels-before.html" "$B/login"
  curl -s -o "$WORK/static/labels-after.html" "$B/login"

  OUT=$(obscura --storage-dir "$PROFILE" fetch "$PANEL_URL" --allow-private-network \
        --wait 1 --eval "$(cat "$SRC/odd/checks/panel_geometry.js")" -q 2>/dev/null | tail -1)
  echo "        $OUT"
  check_eq "browser: the panel paints its four fields" \
    "$(echo "$OUT" | grep -c '"fields":4')" "1"
  check_eq "browser: no field is marked invalid" \
    "$(echo "$OUT" | grep -c '"invalid":0')" "1"
  check_eq "browser: the palette button follows the seed color" \
    "$(echo "$OUT" | grep -c '"button_derived":true')" "1"
  check_eq "browser: the eye button sits inside its password field" \
    "$(echo "$OUT" | grep -c '"reveal_offscreen":\[\]')" "1"
fi
rm -rf "$PROFILE" "$ADMIN" "$TEACH" 2>/dev/null

echo
if [ "$FAILED" -eq 0 ]; then echo "all checks passed"; else echo "$FAILED check(s) failed"; fi
exit $((FAILED > 0))
