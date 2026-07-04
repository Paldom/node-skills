#!/usr/bin/env python3
"""Deterministic npm supply-chain audit of a repository.

Usage: audit_supply_chain.py [--root DIR]
ERROR (exit 1): no lockfile, bare `npm install`/`pnpm install` (non-frozen) in
CI, blanket auto-merge of bot PRs detected in workflows. WARN: Dependabot
missing/without cooldown or groups, no install-script policy for the repo's
package manager, unpinned third-party actions (detail via node-ci's checker).
Stdlib only; line-based heuristics - it flags, humans/agents disposition.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

LOCKFILES = {"package-lock.json": "npm", "pnpm-lock.yaml": "pnpm", "yarn.lock": "yarn", "bun.lockb": "bun", "bun.lock": "bun"}
# Bare installs: `npm install`/`npm i`/pnpm/yarn install without a frozen flag,
# or with the frozen flag explicitly disabled (=false). Global tool installs
# (-g/--global) are not lockfile installs and are ignored here.
BARE_INSTALL_RE = re.compile(
    r"\b(npm\s+(install|i)\b|pnpm\s+install\b|yarn\s+install\b)"
    r"(?![^\n]*(-g\b|--global\b))"
    r"(?![^\n]*((--frozen-lockfile|--immutable)(?!=false)|--ci\b))")
FROZEN_DISABLED_RE = re.compile(r"--(frozen-lockfile|immutable)=false")
AUTOMERGE_RE = re.compile(r"gh\s+pr\s+merge[^\n]*--auto|automerge:\s*true|auto-merge", re.I)
DEPENDABOT_ACTOR_RE = re.compile(r"dependabot|renovate", re.I)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, default=Path("."))
    root = ap.parse_args().root.resolve()
    errors = 0

    def report(level: str, msg: str) -> None:
        nonlocal errors
        if level == "ERROR":
            errors += 1
        print(f"{level}: {msg}")

    # 1. Lockfile + package manager
    found = {n: pm for n, pm in LOCKFILES.items() if (root / n).is_file()}
    if not found:
        report("ERROR", "no lockfile committed - installs are unpinned")
        pm = None
    else:
        pm = list(found.values())[0]
        print(f"INFO: lockfile(s): {', '.join(found)} (package manager: {pm})")
        if len(found) > 1:
            report("WARN", "multiple lockfiles - pick one package manager and delete the rest")

    # 2. CI install commands
    wf_dir = root / ".github" / "workflows"
    wf_files = sorted(list(wf_dir.glob("*.y*ml"))) if wf_dir.is_dir() else []
    for f in wf_files:
        text = f.read_text(encoding="utf-8", errors="replace")
        rel = f.relative_to(root)
        for i, ln in enumerate(text.splitlines(), 1):
            if "npm ci" in ln:
                continue
            if BARE_INSTALL_RE.search(ln) or FROZEN_DISABLED_RE.search(ln):
                report("ERROR", f"{rel}:{i}: non-frozen install in CI ({ln.strip()[:80]}) - "
                                "use npm ci / pnpm install --frozen-lockfile / yarn --immutable")
        if AUTOMERGE_RE.search(text) and DEPENDABOT_ACTOR_RE.search(text):
            report("ERROR", f"{rel}: bot-PR auto-merge detected - bot PRs need the same CI+review gate as humans")

    # 3. Dependabot config
    dep = root / ".github" / "dependabot.yml"
    if not dep.is_file():
        report("WARN", "no .github/dependabot.yml - no automated dependency updates")
    else:
        text = dep.read_text(encoding="utf-8", errors="replace")
        if "cooldown" not in text:
            report("WARN", "dependabot.yml has no cooldown - fresh releases install immediately "
                           "(note: cooldown never covers transitive npm deps; security PRs bypass it)")
        if "groups" not in text:
            report("WARN", "dependabot.yml has no groups - expect PR noise")
        if "github-actions" not in text:
            report("WARN", "dependabot.yml does not cover the github-actions ecosystem")

    # 4. Install-script policy for the actual package manager
    pkg_path = root / "package.json"
    pkg = {}
    if pkg_path.is_file():
        try:
            pkg = json.loads(pkg_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            report("ERROR", "package.json is not valid JSON")
    if pm == "pnpm":
        pnpm_cfg = (pkg.get("pnpm") or {})
        ws = (root / "pnpm-workspace.yaml")
        ws_text = ws.read_text(encoding="utf-8", errors="replace") if ws.is_file() else ""
        if "onlyBuiltDependencies" not in pnpm_cfg and "onlyBuiltDependencies" not in ws_text:
            report("WARN", "pnpm without an onlyBuiltDependencies allowlist (package.json#pnpm or "
                           "pnpm-workspace.yaml) - install scripts run unconstrained")
    elif pm == "npm":
        npmrc = (root / ".npmrc").read_text(encoding="utf-8", errors="replace") if (root / ".npmrc").is_file() else ""
        if re.search(r"^\s*ignore-scripts\s*=\s*false", npmrc, re.M):
            report("WARN", ".npmrc explicitly sets ignore-scripts=false - lifecycle scripts run; "
                           "make this a deliberate, documented choice")
        elif "ignore-scripts" not in npmrc:
            report("WARN", "npm without ignore-scripts policy in .npmrc - verify your npm major's default "
                           "lifecycle-script behavior against npm docs and set policy explicitly")
    elif pm == "yarn":
        yarnrc = (root / ".yarnrc.yml").read_text(encoding="utf-8", errors="replace") if (root / ".yarnrc.yml").is_file() else ""
        if re.search(r"^\s*enableScripts:\s*true", yarnrc, re.M):
            report("WARN", ".yarnrc.yml explicitly sets enableScripts: true - install scripts run; "
                           "make this a deliberate, documented choice")
        elif "enableScripts" not in yarnrc:
            report("WARN", "yarn without enableScripts policy in .yarnrc.yml")

    # 5. Unpinned third-party actions (summary; detail lives in node-ci's checker)
    unpinned = 0
    for f in wf_files:
        for ln in f.read_text(encoding="utf-8", errors="replace").splitlines():
            m = re.match(r"^\s*-?\s*uses:\s*([^\s#]+)", ln)
            if m and not m.group(1).startswith(("actions/", "github/", "./", "docker://")) \
                    and not re.search(r"@[0-9a-f]{40}$", m.group(1)):
                unpinned += 1
    if unpinned:
        report("WARN", f"{unpinned} third-party action reference(s) not SHA-pinned "
                       "(run node-ci's check_workflows.py for locations)")

    print(f"{'FAIL' if errors else 'OK'}: {errors} error(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
