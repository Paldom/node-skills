# Supply-Chain Playbook (npm dependencies + CI workflows)

Harden a Node/TS repo against dependency and workflow supply-chain attacks.
Scope: what enters `node_modules`, what runs at install time, how updates
arrive, and how CI consumes third-party actions.

Out of scope — route elsewhere:
- GitHub org/repo settings (branch rulesets, secret scanning, push protection,
  Actions allow-list policy) → owned by the GitHub-settings skills repo.
- Publishing your own package (release workflow, generating provenance,
  setting up trusted publishing in CI) → `node-release` skill. This file covers
  only the credential-hygiene side of tokens.

## Contents

- [Layered model](#layered-model)
- [Lockfile discipline](#lockfile-discipline)
- [Cooldown: minimum release age](#cooldown-minimum-release-age)
- [Dependabot configuration](#dependabot-configuration)
- [Install-script policy per package manager](#install-script-policy-per-package-manager)
- [Provenance and signature verification](#provenance-and-signature-verification)
- [npm token policy](#npm-token-policy)
- [GitHub Actions hygiene](#github-actions-hygiene)
- [Incident response: compromised upstream dependency](#incident-response-compromised-upstream-dependency)

## Layered model

Apply defenses in layers; each catches what the previous one misses.

| Layer | Question it answers | Controls |
|---|---|---|
| Resolution | What versions may enter the tree? | committed lockfile, minimum release age |
| Installation | What executes on `install`? | install-script allowlists, frozen installs |
| Update flow | How do new versions arrive? | Dependabot weekly + cooldown, human review of bot PRs |
| Origin | Who built and published this? | `npm audit signatures`, provenance, token hygiene |
| CI workflows | What third-party code runs in CI? | SHA-pinned actions, zizmor, actionlint |
| Response | What when a dep is compromised anyway? | incident checklist below |

No single layer is sufficient: cooldowns don't stop patient attackers,
script-blocking doesn't stop runtime-stage malware, provenance proves origin
not safety. Stack them.

## Lockfile discipline

- Commit the lockfile. Always — applications AND libraries. A library's
  lockfile is not published, but it pins what runs on maintainer machines and
  in CI, which is exactly where supply-chain attacks execute.
- One package manager, one lockfile. Delete stray lockfiles from other
  managers. Declare the manager in `package.json` (`"packageManager":
  "pnpm@<exact-version>"`) so tooling and teammates resolve the same one
  (activation mechanics — Corepack vs. standalone installs — are in flux;
  verify current status at use time).
- CI must install frozen (fail on any lockfile drift, never write it):
  - npm: `npm ci`
  - pnpm: `pnpm install --frozen-lockfile` (defaults to true on CI, but pass
    the flag explicitly — do not rely on CI detection; verify:
    https://pnpm.io/cli/install)
  - yarn (Berry): `yarn install --immutable` (again: explicit flag, don't
    rely on the CI-only default of `enableImmutableInstalls`)
- Review lockfile diffs in PRs like code. Red flags: `resolved` URLs pointing
  anywhere but the expected registry, `integrity` hash changes without a
  version change, new git/tarball-URL dependencies, huge unexplained churn.
- Never run `npm install`/`npm i`, bare `pnpm install`/`yarn install`, or any
  install with the frozen flag disabled (`--frozen-lockfile=false`,
  `--immutable=false`) in CI or in bot PR pipelines; a writable lockfile in
  automation is an injection point (`scripts/audit_supply_chain.py` errors on
  all of these forms).

## Cooldown: minimum release age

Most compromised releases are detected and unpublished within days. Refusing
brand-new versions at *resolution time* protects even fresh installs and
transitive deps (which Dependabot's cooldown does not — see caveats below).

- npm ≥ 11.10.0 — `.npmrc`, value in days, default null (as of mid-2026,
  verify: https://docs.npmjs.com/cli/v11/using-npm/config#min-release-age):

  ```ini
  min-release-age=7
  min-release-age-exclude[]=@yourorg/*
  ```

- pnpm — `minimumReleaseAge` in **minutes** (added v10.16.0; docs list default
  1440 = 1 day as of mid-2026, but set it explicitly — verify:
  https://pnpm.io/settings):

  ```yaml
  # pnpm-workspace.yaml
  minimumReleaseAge: 10080          # 7 days, in minutes
  minimumReleaseAgeExclude:
    - "@yourorg/*"
  ```

- yarn (Berry) — `npmMinimalAgeGate` in `.yarnrc.yml`: minimum age, by npm
  registry publish date, a version must reach before yarn considers it for
  installation; documented default `1w` (as of mid-2026; verify:
  https://yarnpkg.com/configuration/yarnrc). Set it explicitly, e.g.
  `npmMinimalAgeGate: "1w"`.

Pick 3–7 days for apps; exclude your own org scope so internal releases flow.

## Dependabot configuration

Two ecosystems minimum: `npm` and `github-actions`. Weekly, grouped, with
cooldown. Full explicit config (`.github/dependabot.yml`) — key names verified
against https://docs.github.com/en/code-security/reference/supply-chain-security/dependabot-options-reference
(as of mid-2026):

```yaml
version: 2
updates:
  - package-ecosystem: "npm"
    directory: "/"
    schedule:
      interval: "weekly"
      day: "monday"
      time: "06:00"
      timezone: "Etc/UTC"
    open-pull-requests-limit: 10
    cooldown:
      default-days: 7
      semver-major-days: 14
      semver-minor-days: 7
      semver-patch-days: 3
    groups:
      npm-minor-patch:
        applies-to: version-updates
        patterns: ["*"]
        update-types: ["minor", "patch"]
      # majors arrive as individual PRs — review each on its own

  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
      day: "monday"
      time: "06:00"
      timezone: "Etc/UTC"
    cooldown:
      default-days: 7
    groups:
      actions-all:
        applies-to: version-updates
        patterns: ["*"]
```

Verified caveats — design these into your process:

- Cooldown applies to **version updates only; security updates bypass it by
  design**, so CVE fixes still land promptly. (Open bug reports exist about
  security updates sometimes respecting cooldown — e.g.
  dependabot-core#13979; verify current behavior at use time.)
- Dependabot version updates for npm cover **direct (manifest) dependencies**;
  transitive, lockfile-only deps are not independently version-updated, so
  cooldown never gates them. That gap is exactly what
  `min-release-age` / `minimumReleaseAge` (above) closes.
- Dependabot **alerts** for GitHub Actions are only generated for actions
  referenced by semver tag — **not for SHA-pinned actions** (verify:
  https://docs.github.com/code-security/dependabot/dependabot-alerts/about-dependabot-alerts).
  Keep the `github-actions` *version updates* ecosystem enabled: it does bump
  SHA pins, which is your update path for pinned actions.

Rule: **never blanket-auto-merge bot PRs.** Auto-merge converts Dependabot
into an unattended supply-chain conveyor — cooldown then merely delays the
compromise instead of letting a human catch it. If you automate anything,
limit it to narrowly scoped groups (e.g. patch-only, internal-scope) with CI
green AND a human-visible merge queue; default is human review of the grouped
weekly PR (minutes of work thanks to grouping).

## Install-script policy per package manager

Lifecycle scripts (`preinstall`/`install`/`postinstall`) are the #1 execution
vector for malicious packages. Behavior differs sharply per manager AND per
major version — be precise:

- **npm 11** (current stable line, as of mid-2026): dependency scripts **run
  by default** (`ignore-scripts` defaults to `false`). Opt out in `.npmrc`:

  ```ini
  ignore-scripts=true
  ```

  Caveat: this also skips *your own* `prepare`/`postinstall` and the pre/post
  hooks of `npm run` scripts — run needed builds explicitly.
- **npm 12** (announced June 2026, estimated July 2026; not confirmed shipped
  as of this writing — verify what you actually run:
  https://github.blog/changelog/2026-06-09-upcoming-breaking-changes-for-npm-v12/):
  flips the default — dependency install scripts (including implicit
  `node-gyp` builds) are **blocked unless explicitly allowed**. Also `--allow-git`
  and `--allow-remote` default to `none`, blocking git/tarball-URL deps.
  Prepare on npm ≥ 11.16.0 (advisory warnings): `npm approve-scripts
  --allow-scripts-pending` to list, then `npm approve-scripts` /
  `npm deny-scripts`; commit the resulting allowlist in `package.json`.
- **pnpm ≥ 10**: dependency scripts **blocked by default**. pnpm 10 allowlist:
  `onlyBuiltDependencies` — in `pnpm-workspace.yaml` or `package.json#pnpm`
  (both locations count as policy). Removed in pnpm 11 in favor of
  `allowBuilds` (added v10.26.0), a map of package matchers to allow/deny;
  `strictDepBuilds` (added v10.3.0, default true) fails the install on
  unreviewed build scripts (as of mid-2026; verify: https://pnpm.io/settings):

  ```yaml
  # pnpm-workspace.yaml (pnpm ≥ 10.26)
  strictDepBuilds: true
  allowBuilds:
    esbuild: true
    better-sqlite3: true
  ```

- **yarn (Berry)**: `enableScripts` in `.yarnrc.yml` — default flipped to
  `false` in yarn 4.14.0 (release notes:
  https://github.com/yarnpkg/berry/releases/tag/%40yarnpkg%2Fcli%2F4.14.0);
  earlier releases default `true`. Set it explicitly either way, and treat a
  lingering explicit `enableScripts: true` (e.g. left over from an upgrade)
  as a policy exception to remove or justify. Re-enable per package via
  `dependenciesMeta` (verify exact combination:
  https://yarnpkg.com/configuration/yarnrc):

  ```yaml
  # .yarnrc.yml
  enableScripts: false
  ```

- **bun**: also blocks unapproved dependency scripts (`trustedDependencies`) —
  verify at use time if bun is in play.

Policy: keep scripts off globally; allowlist only packages that genuinely need
native builds (check each: does it work scriptless via prebuilt binaries?).
The allowlist is code — review additions in PRs. An explicit global opt-out
(`ignore-scripts=false` in `.npmrc`, `enableScripts: true` in `.yarnrc.yml`)
is a declared decision to run every dependency's scripts — the audit script
flags it; keep it only with documented justification.

## Provenance and signature verification

`npm audit signatures` verifies registry signatures and provenance
attestations of downloaded packages — for registries that publish signing
keys per npm's conventions; in practice the public npm registry (as of
mid-2026, verify: https://docs.npmjs.com/cli/v11/commands/npm-audit):

```bash
npm audit signatures
# JSON with full attestation bundles:
npm audit signatures --json --include-attestations
```

Run it in CI after the frozen install. Understand the limits:

- Provenance proves **origin, not safety**: the package verifiably came from a
  given repo + CI workflow. A compromised maintainer account with a hijacked
  workflow produces validly-attested malware.
- Coverage is partial — many packages publish without provenance; treat a
  *change* (package used to attest, now doesn't; repo slug changed) as a red
  flag rather than absence as a blocker.
- The attestation format evolves; keep the npm CLI current for verification.

## npm token policy

Status as of mid-2026 (verify:
https://github.blog/changelog/2025-12-09-npm-classic-tokens-revoked-session-based-auth-and-cli-token-management-now-available/):

- **Classic tokens are dead** — creation disabled Nov 2025, all existing ones
  revoked Dec 9, 2025. Anything still referencing one is broken; delete it.
- **Granular tokens with write access are capped at 90-day lifetime.** Treat
  any long-lived write token in CI secrets as a liability: inventory, expire,
  replace with trusted publishing.
- `npm login` now issues a **2-hour session token** with 2FA enforced for
  publish — fine for humans, wrong for automation.
- **Prefer trusted publishing (OIDC)** — no long-lived secret at all; then
  enforce it: package **Settings → Publishing access → "Require two-factor
  authentication and disallow tokens"** blocks token-based publishing while
  trusted publishers keep working (verify: https://docs.npmjs.com/trusted-publishers).
  Setting up the publish workflow itself → `node-release` skill.
- Read-only needs (private registry installs in CI): granular token, read
  scope, narrowest package/org scope, shortest expiry, one token per pipeline.

## GitHub Actions hygiene

Third-party actions are dependencies that run with your CI credentials.

- **Pin every third-party action to a full commit SHA**, with the version as a
  trailing comment (Dependabot reads and maintains this comment format when
  bumping pins):

  ```yaml
  - uses: some-org/some-action@<full-40-char-commit-sha> # v3.2.1
  ```

  Mutable tags (`@v3`, `@main`) let a compromised or force-pushed upstream
  ref execute arbitrary code in your workflows. Decide your own policy for
  `actions/*` (GitHub-owned) — pinning everything is the simple rule.
- **Lint workflows in CI**, both tools, explicit invocation:
  - `zizmor` — GitHub Actions security auditor; relevant audits (names
    verified against https://docs.zizmor.sh/audits/): `unpinned-uses`
    (non-SHA refs), `ref-confusion` (ambiguous branch/tag refs),
    `impostor-commit` (fork-network commit spoofing), `ref-version-mismatch`
    and `stale-action-refs` (pin/comment drift). Run
    `zizmor .github/workflows/` (install per https://docs.zizmor.sh/installation/).
  - `actionlint` — workflow syntax/semantics/shell checks:
    https://github.com/rhysd/actionlint
- Remember the Dependabot caveat above: SHA-pinned actions get **no
  Dependabot alerts**; the version-updates ecosystem + zizmor are your
  freshness and integrity signals.
- Repo-level Actions policies (allow-lists, forcing SHA pins org-wide) exist
  but are repo settings → GitHub-settings skills repo, not here.

## Incident response: compromised upstream dependency

When an advisory drops for package `P`, versions `X..Y`, published during
window `T1..T2`:

1. **Determine exposure.** Search lockfiles on all active branches and
   deployed refs — the lockfile is ground truth, not `package.json` ranges:
   `npm ls P --all` / `pnpm why P` / `yarn why P`, plus grep the lockfile for
   `P@` entries. Check every repo/workspace, not just the one at hand.
2. **Determine execution.** Not-installed ≠ safe only if truly never
   resolved: check CI logs and developer installs during `T1..T2`. Note
   whether install scripts could have run (if your script policy blocked
   them, the install-time payload was neutered — runtime payloads still
   count once the code was imported).
3. **Contain.** Force a known-good version even where transitive:
   - npm `package.json`: `"overrides": { "P": "<known-good>" }`
   - pnpm: `overrides` (location moved across majors — verify:
     https://pnpm.io/settings)
   - yarn `package.json`: `"resolutions": { "P": "<known-good>" }`
   Reinstall, confirm the lockfile shows only the pinned version, commit.
4. **Rotate credentials** reachable from any machine/CI job that ran the
   compromised code during the window: npm tokens, GitHub tokens/SSH keys,
   cloud creds, `.env` secrets, browser-stored sessions if a dev box ran it.
   Assume exfiltration; rotation is cheap.
5. **Document the window.** Record: affected package/versions, `T1..T2`,
   where it was installed/executed, first clean commit per branch, creds
   rotated, override applied. This is what audits and downstream consumers
   will ask for.
6. **Unwind deliberately.** Keep the override until the upstream publishes a
   verified-clean release *older than your cooldown or explicitly vetted*;
   removing the pin the day a "fixed" version appears defeats the cooldown
   layer.
7. If your own published package consumed `P` in an affected build, that's a
   downstream-notification/republish problem → `node-release` skill.
