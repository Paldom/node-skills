---
name: node-release
description: Cuts and automates npm releases - Changesets, semantic-release or release-please, npm trusted publishing (OIDC) with provenance, the first-publish bootstrap, staged publishing, changelogs and tags. Use when the user asks to release, version, publish to npm, or remove tokens from publish workflows. Not for package exports/bundling artifacts or verifying dependency provenance.
license: MIT
argument-hint: [setup|migrate-oidc|troubleshoot]
---

# node-release

Automates versioning and npm publishing with **no long-lived secrets and no
guessed facts**. The failures this skill fixes: models wire `NPM_TOKEN` secrets
in 2026, miss that a package's *first* version can't be published via OIDC, get
the trusted-publisher registration subtly wrong (case, filename, indirection),
and leave releases half-done when publish fails after tagging.

## When NOT to use

- Exports maps, bundling, tarball contents → `node-packaging` (release assumes
  its gates already pass).
- Verifying *dependencies'* provenance → `node-supply-chain`.
- Test/lint CI → `node-ci`.

## Workflow

1. **Pick the release tool** by workflow reality (decision table in
   `references/release-playbook.md`): Changesets (human-written notes,
   monorepos), semantic-release (strict conventional commits, fully
   autonomous), release-please (PR-gated review of each release).
2. **Trusted publishing (OIDC) — the default auth**; all requirements are
   version-gated in the playbook with the official npm doc links (CLI/Node
   minimums on the runner, GitHub-hosted runners, exact repo + workflow-filename
   registration match, `workflow_call` indirection caveat). Provenance is
   attached automatically under trusted publishing.
3. **Bootstrap gotcha — say it before it bites**: a brand-new package cannot be
   first-published via OIDC; the playbook's bootstrap procedure covers the one
   manual publish, then registration, then token revocation and account-level
   trusted-publishing-only enforcement.
4. **Write the publish workflow** from the playbook's YAML: minimal permissions
   (`id-token: write`, `contents: read/write` only as needed), SHA-pinned
   third-party actions (consistent with `node-supply-chain` policy), publish
   gated on the `node-packaging` checks.
5. **Failure-ordering discipline**: publish before tagging (or make retries
   idempotent); never delete published tags — releases are immutable.
6. **Verify end-to-end**: dry-run, then a real publish of a prerelease/dist-tag
   where possible; confirm provenance on the registry page; only then revoke
   legacy tokens.

## Output spec

A working automated release pipeline: version + changelog + tag + npm publish
with provenance, zero long-lived registry secrets after cutover, bootstrap and
rollback procedures documented in the repo, staged/prerelease channel decided
deliberately.

## Gotchas

- Trusted-publisher registration is exact-match: owner/repo casing and workflow
  filename including extension; publishing from a reusable (`workflow_call`)
  workflow validates against the *calling* file.
- OIDC does not make a compromised workflow safe — it removes stored-secret
  theft; workflow-file review still matters (CODEOWNERS on `.github/`).
- Tag-then-fail leaves consumers seeing a version npm doesn't have — ordering
  or idempotency, pick one explicitly.
- All npm-side specifics (minimums, staged publishing, token lifetimes) drift:
  the playbook version-gates each with its primary source — re-verify on setup.

## Files

- `references/release-playbook.md` — tool decision table, OIDC setup with
  version-gated requirements + doc links, bootstrap procedure, publish workflow
  YAML, failure-ordering patterns, dist-tag/prerelease guidance.
