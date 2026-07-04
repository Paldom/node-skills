#!/usr/bin/env bash
# Publish-readiness gate: tarball inspection + publint --strict + arethetypeswrong,
# all run against the SAME packed artifact.
# Usage: check_package.sh [package-dir]   (default: .)
# Exits non-zero on any finding. Requires Node >= 18 with npx.
set -uo pipefail

dir="${1:-.}"
cd "$dir" || { echo "ERROR: cannot cd to $dir" >&2; exit 1; }
[ -f package.json ] || { echo "ERROR: no package.json in $dir" >&2; exit 1; }
command -v npx >/dev/null 2>&1 || { echo "ERROR: npx (Node.js >= 18) required" >&2; exit 1; }

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
fail=0

echo "== npm pack --json (tarball contents) =="
if ! npm pack --json --pack-destination "$tmp" > "$tmp/pack.json" 2>"$tmp/pack.err"; then
  cat "$tmp/pack.err" >&2
  echo "ERROR: npm pack failed" >&2
  exit 1
fi
# Parse the machine-readable file list; grep of human 'npm notice' output is not reliable.
if ! python3 - "$tmp/pack.json" <<'PY'
import json, re, sys
data = json.load(open(sys.argv[1]))
files = [f["path"] for f in data[0].get("files", [])]
bad = [p for p in files if re.search(
    r"(^|/)(\.env[^/]*$|\.local/|node_modules/|\.github/|coverage/|\.DS_Store$)"
    r"|\.(test|spec)\.[cm]?[jt]sx?$", p)]
print(f"{len(files)} files in tarball")
if bad:
    print("ERROR: tarball contains files that should not ship:")
    for p in bad:
        print(f"  - {p}")
    sys.exit(1)
PY
then
  echo "ERROR: fix the files whitelist (package.json#files)" >&2
  fail=1
fi
tarball="$tmp/$(python3 -c "import json,sys;print(json.load(open('$tmp/pack.json'))[0]['filename'])")"

echo "== publint --strict (against the packed tarball) =="
# Major-pinned for reproducibility; exact-pin inside your repo and bump deliberately.
if ! npx -y publint@0 --strict "$tarball"; then
  echo "ERROR: publint --strict reported problems" >&2
  fail=1
fi

echo "== arethetypeswrong (against the same tarball) =="
if ! npx -y @arethetypeswrong/cli@0 "$tarball"; then
  echo "ERROR: arethetypeswrong reported resolution problems" >&2
  fail=1
fi

[ "$fail" -eq 0 ] && echo "OK: tarball, publint --strict, and attw all clean"
exit "$fail"
