#!/bin/bash
# No hosting credentials are needed: this repository is public.
set -euo pipefail
umask 022
BASE=/home/carloertolanet/.deployments/epicure
PUBLIC=/home/carloertolanet/epicure-public
REPO=/home/carloertolanet/repositories/epicure
GIT=/usr/local/cpanel/3rdparty/lib/path-bin/git
mkdir -p "$BASE" "$PUBLIC/releases"
exec 9>"$BASE/deploy.lock"
/usr/bin/flock -n 9 || exit 0
cd "$REPO"
"$GIT" fetch --quiet origin main
SHA=$("$GIT" rev-parse refs/remotes/origin/main)
if [ -f "$PUBLIC/current/.release" ] && [ "$(cat "$PUBLIC/current/.release")" = "$SHA" ]; then exit 0; fi
RELEASE="$PUBLIC/releases/$SHA"
if [ ! -d "$RELEASE/public" ]; then
  mkdir -p "$RELEASE"
  "$GIT" archive "$SHA" public | /bin/tar -x -C "$RELEASE"
fi
test -s "$RELEASE/public/index.html"
test -s "$RELEASE/public/app.js"
test -s "$RELEASE/public/data/foods.json"
printf '%s\n' "$SHA" > "$RELEASE/public/.release"
# Same-filesystem rename switches the served version atomically.
/bin/ln -sfn "$RELEASE/public" "$PUBLIC/current.next"
/bin/mv -Tf "$PUBLIC/current.next" "$PUBLIC/current"
printf '%s Deployed %s\n' "$(date -u +%FT%TZ)" "$SHA"
# Retain releases for a straightforward manual rollback. No data is deleted.
