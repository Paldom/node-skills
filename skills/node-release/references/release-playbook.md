# Release playbook: versioning + npm publishing automation

Scope: choosing and configuring a release tool, and publishing to npm from CI
safely. NOT in scope: package `exports`/bundling (see `node-packaging`), test CI
(see `node-ci`), dependency hygiene and verifying provenance of packages you
*install* (see `node-supply-chain`).

## Contents

- [Pick the release tool](#pick-the-release-tool)
- [Changesets configuration](#changesets-configuration)
- [semantic-release configuration](#semantic-release-configuration)
- [release-please configuration](#release-please-configuration)
- [npm trusted publishing (OIDC)](#npm-trusted-publishing-oidc)
- [First-publish bootstrap](#first-publish-bootstrap)
- [Lock the package down after OIDC works](#lock-the-package-down-after-oidc-works)
- [Staged publishing](#staged-publishing)
- [Minimal publish workflow (GitHub Actions)](#minimal-publish-workflow-github-actions)
- [Partial-failure ordering](#partial-failure-ordering)
- [Prerelease channels and dist-tags](#prerelease-channels-and-dist-tags)
- [Routing](#routing)

## Pick the release tool

Decide on one axis: how much human judgment goes into version bumps and notes.

| Tool | Model | Pick when |
|---|---|---|
| **Changesets** | Contributors write intent files per PR; bot PR accumulates them; merge = version + publish | Monorepos; you want human-written release notes; multi-package independent versioning |
| **semantic-release** | Fully autonomous: Conventional Commits drive bump, notes, tag, publish on every push to a release branch | Single packages; team reliably writes conventional commits; zero-touch releases |
| **release-please** | Bot maintains a long-lived Release PR from conventional commits; merging it tags a release; publish is a separate step you own | You want conventional-commit automation *plus* a human merge gate before anything ships |

Rules of thumb:

- Monorepo with independently versioned packages: Changesets. It is the only one
  of the three built around that shape (`fixed`/`linked` groups, internal
  dependency bumps).
- Enforce Conventional Commits in CI (commitlint) *before* adopting
  semantic-release or release-please — a mistyped commit silently produces a
  wrong bump or no release.
- All three only automate versioning/notes/tagging; the npm publish step itself
  should follow the [trusted publishing](#npm-trusted-publishing-oidc) section
  regardless of tool.

Versions as of mid-2026 (verify at use time): `@changesets/cli` 2.31.0 stable
(3.0.0 in `next` prerelease), `semantic-release` 25.0.x (requires Node
`^22.14.0 || >=24.10.0`), `@semantic-release/npm` 13.1.x,
`release-please-action` v5 (v4 still widely used).

## Changesets configuration

Write the full config; do not rely on generated defaults drifting across
versions. Docs: https://github.com/changesets/changesets/blob/main/docs/config-file-options.md

`.changeset/config.json` (keep the `$schema` line `npx changeset init` writes
for your installed version):

```json
{
  "changelog": "@changesets/cli/changelog",
  "commit": false,
  "access": "public",
  "baseBranch": "main",
  "updateInternalDependencies": "patch",
  "fixed": [],
  "linked": [],
  "ignore": [],
  "privatePackages": { "version": true, "tag": false }
}
```

- `access: "public"` is mandatory for scoped public packages — the default is
  `restricted` and the publish will fail or go private.
- `baseBranch` defaults to `master`; set it explicitly.
- `fixed`: packages that always bump together to the same version;
  `linked`: packages that share a version number when bumped.
- Flow: contributors run `npx changeset` in PRs; `changesets/action` opens a
  "Version Packages" PR; merging it runs your publish command.
  `changeset publish` skips versions already on the registry, so retries are
  idempotent.

## semantic-release configuration

Explicit `.releaserc.json` — never rely on the implicit default plugin list or
default preset:

```json
{
  "branches": [
    "main",
    { "name": "next", "channel": "next", "prerelease": true }
  ],
  "plugins": [
    ["@semantic-release/commit-analyzer", { "preset": "conventionalcommits" }],
    ["@semantic-release/release-notes-generator", { "preset": "conventionalcommits" }],
    ["@semantic-release/npm", { "npmPublish": true }],
    ["@semantic-release/github", { "successComment": false, "failComment": false }]
  ]
}
```

- semantic-release v25 supports npm trusted publishing via
  `@semantic-release/npm` v13: grant `id-token: write` and drop `NPM_TOKEN`
  entirely, as of mid-2026 (verify:
  https://semantic-release.gitbook.io/semantic-release/recipes/ci-configurations/github-actions).
- It still needs a GitHub token (`GITHUB_TOKEN`) with `contents: write` to push
  the tag and create the release.
- **Half-release failure mode**: core creates and pushes the git tag *before*
  any plugin's publish step (steps: … → Create Git tag → Prepare → Publish;
  verify: https://github.com/semantic-release/semantic-release#release-steps).
  Plugin order (`npm` before `github`) only orders publish-step plugins — a
  failed `npm publish` still leaves a pushed tag with nothing on the registry,
  and a plain rerun will NOT retry it (the tag exists, so no new release).
- Recovery: never delete the pushed tag — check it out and run an
  `npm view`-guarded publish ([minimal workflow](#minimal-publish-workflow-github-actions)).
  For strict publish-before-tag, semantic-release cannot provide it — use
  Changesets (publishes, then tags) or a custom flow
  ([Partial-failure ordering](#partial-failure-ordering)).

## release-please configuration

`release-please-config.json`:

```json
{
  "release-type": "node",
  "include-component-in-tag": false,
  "packages": { ".": {} }
}
```

`.release-please-manifest.json` (seed with the current released version):

```json
{ ".": "1.4.2" }
```

Workflow step (it does NOT publish to npm — it only maintains the Release PR
and tags). Rerun trap: after a created tag/Release with a failed publish,
reruns report `release_created` as false, so a bare `if: release_created`
skips the recovery publish forever. Guard on the registry:

```yaml
- id: release
  uses: googleapis/release-please-action@45996ed1f6d02564a971a2fa1b5860e934307cf7 # v5.0.0 — re-resolve SHA at use time
  with:
    token: ${{ secrets.GITHUB_TOKEN }}
- name: Publish (idempotent — safe to rerun)
  if: ${{ steps.release.outputs.release_created == 'true' || github.event_name == 'workflow_dispatch' }}
  run: |
    PKG="$(node -p "require('./package.json').name")@$(node -p "require('./package.json').version")"
    if npm view "$PKG" version >/dev/null 2>&1; then
      echo "$PKG already published — skipping"
    else
      npm publish --access public
    fi
```

The `workflow_dispatch` arm is the manual recovery path (check out the release
tag when dispatching). Sturdier: publish from a separate workflow on
`release: types: [published]` — the [minimal workflow](#minimal-publish-workflow-github-actions)
below checks out the tagged ref, so rerunning it publishes from the existing tag.

Docs: https://github.com/googleapis/release-please-action

## npm trusted publishing (OIDC)

Prefer OIDC over any npm token in CI. All facts below are as of mid-2026
(verify: https://docs.npmjs.com/trusted-publishers/):

- Requires **npm CLI >= 11.5.1** and **Node >= 22.14.0**. GitHub runner images
  may bundle an older npm — upgrade explicitly in the workflow
  (`npm install -g npm@latest`) and fail fast if `npm --version` < 11.5.1.
- Supported CI: GitHub Actions on **GitHub-hosted runners only** (self-hosted
  not supported yet), GitLab.com shared runners, CircleCI cloud.
- Configure per package (Settings → Trusted Publisher on npmjs.com, or
  `npm trust github --repo owner/name --file release.yml --allow-publish`;
  the `npm trust` command needs npm >= 11.15.0, verify:
  https://docs.npmjs.com/cli/v11/commands/npm-trust/). One trusted publisher
  per package.
- Matching is **exact and case-sensitive**: owner, repository name, and
  workflow **filename only** (with `.yml`/`.yaml` extension, no path).
  Renaming the workflow file breaks publishing until you update the config.
- **`workflow_call` caveat**: if a reusable workflow runs `npm publish`,
  validation matches the *calling* (parent) workflow's filename, not the child
  containing the publish step — configure the parent's filename, and grant
  `id-token: write` in both parent and child.
- **Provenance is generated by default** when publishing via OIDC from GitHub
  Actions or GitLab (public repo + public package only; not on CircleCI). The
  `repository.url` in `package.json` must exactly match the repo or provenance
  verification fails.
- The environment field is optional; if you use a GitHub deployment
  environment for approval gates, add it to the trusted publisher config too.

## First-publish bootstrap

Trusted publishing cannot create a package: the package must already exist on
the registry before a trusted publisher can be configured, as of mid-2026
(verify: https://github.com/npm/cli/issues/8544 — open feature request to
allow OIDC for initial versions; PyPI-style pre-registration does not exist on
npm yet).

Safe bootstrap procedure for a new package:

1. Publish `0.0.1` (or `1.0.0-bootstrap.0` on a non-`latest` tag) locally from
   a clean checkout: `npm publish --access public` with your 2FA-enabled
   account. Prefer an interactive 2FA publish over minting a token at all.
2. If CI must do the first publish, create a **granular access token** scoped
   to only this package, 7-day expiry, use it once, then **revoke it**.
3. Immediately configure the trusted publisher (UI or `npm trust`).
4. Set publishing access to disallow tokens (next section).
5. All subsequent releases go through the OIDC workflow.

## Lock the package down after OIDC works

As of mid-2026 (verify:
https://docs.npmjs.com/requiring-2fa-for-package-publishing-and-settings-modification/
and https://docs.npmjs.com/about-access-tokens/):

- Per package, set Settings → Publishing access to **"Require two-factor
  authentication and disallow tokens"**. Trusted publishers keep working (OIDC
  is not a token in this sense); all granular-token publishes are blocked.
  This is the strongest enforcement — apply it to every package once OIDC is
  proven. The setting is per-package on npmjs.com; no documented CLI toggle
  (verify at use time).
- Token landscape: classic tokens are revoked and can no longer be created
  (since late 2025); granular write tokens default to **7-day** expiry with a
  **90-day maximum** lifetime. Do not build release automation on tokens —
  they now expire by design.

## Staged publishing

Documented as available as of mid-2026; the official docs state no GA date —
verify status at use time (https://docs.npmjs.com/staged-publishing/):

- `npm stage publish` uploads the tarball to a staging queue instead of going
  live; a maintainer reviews (`npm stage list` / `view` / `download`) and
  approves with `npm stage approve <stage-id>` — approval always prompts 2FA,
  staging itself never does, which makes staging CI-friendly.
- Requires npm CLI >= 11.15.0, Node >= 22.14.0, a 2FA-enabled npm account, and
  the package must already exist (staging cannot bootstrap a new package
  either).
- Trusted publisher configs distinguish `--allow-publish` vs
  `--allow-stage-publish`; grant only the one your workflow uses.
- Use it when you want an OIDC pipeline *plus* a human 2FA gate on the exact
  bytes going live. Note tool support may lag (e.g. `changeset publish`
  integration — verify at use time).

## Minimal publish workflow (GitHub Actions)

Least privilege: `contents: read`, `id-token: write`, no npm secret. Pin
actions to full commit SHAs (policy shared with `node-supply-chain`). SHAs
below resolved mid-2026 — re-resolve against each repo's releases page at use
time.

```yaml
name: release
on:
  release:
    types: [published]

permissions: {}

jobs:
  publish:
    runs-on: ubuntu-latest   # must be GitHub-hosted for npm OIDC
    permissions:
      contents: read
      id-token: write        # required for OIDC + provenance
    steps:
      - uses: actions/checkout@9c091bb21b7c1c1d1991bb908d89e4e9dddfe3e0 # v7.0.0
        with:
          persist-credentials: false
      - uses: actions/setup-node@48b55a011bda9f5d6aeb4c2d9c7362e8dae4041e # v6.4.0
        with:
          node-version: 24
          registry-url: "https://registry.npmjs.org"
      - name: Ensure npm supports trusted publishing
        run: |
          npm install -g npm@latest
          npm --version
      - run: npm ci
      - run: npm run build --if-present
      - name: Publish (idempotent)
        run: |
          PKG="$(node -p "require('./package.json').name")@$(node -p "require('./package.json').version")"
          if npm view "$PKG" version >/dev/null 2>&1; then
            echo "$PKG already published — skipping"
          else
            npm publish --access public
          fi
```

No `NODE_AUTH_TOKEN`, no `--provenance` flag needed — OIDC publishes attach
provenance by default. For Changesets, replace the publish step with
`changesets/action@a45c4d594aa4e2c509dc14a9f2b3b67ba3780d0d # v1.9.0` and give
that job `contents: write` + `pull-requests: write` (it pushes the Version
Packages PR) in a *separate* job from the OIDC publish where possible.

## Partial-failure ordering

A release is multiple non-atomic writes (version commit, npm publish, git tag,
GitHub Release). Decide the order and make every step idempotent:

- **Publish-then-tag** (recommended when you control the order; Changesets
  does this — `changeset publish` publishes, then tags): npm publish is the
  step most likely to fail (registry validation, OIDC mismatch) and the
  hardest to undo — a version can never be reused, even after unpublish.
  Tagging after publish means a failed run leaves nothing half-shipped.
- **Tag-then-publish** (semantic-release — core tags before the publish step —
  release-please, tag-triggered workflows): the tag/Release exists before
  publish. Make the publish step an **idempotent retry**: guard with
  `npm view <name>@<version>` (as in the YAML above) so a rerun publishes from
  the existing tag and a duplicate publish becomes a no-op instead of an error.
- Never bump-and-retry a failed publish with a new version to "unstick" CI,
  and never delete a pushed release tag to reset a failed run — fix the cause
  and publish from the tag; otherwise versions, tags, and changelogs desync.
- In monorepos, publish packages in dependency order (Changesets does this) so
  a mid-run failure never leaves a published package depending on an
  unpublished version.

## Prerelease channels and dist-tags

- `latest` is what `npm install <pkg>` resolves — **never** let a prerelease
  land there. Every prerelease publish must pass an explicit tag:
  `npm publish --tag next`.
- Version prereleases as `1.5.0-next.0`, `1.5.0-beta.1` (semver prerelease
  identifiers), matched to a dist-tag channel (`next`, `beta`).
- Changesets: `npx changeset pre enter next` … `pre exit` toggles prerelease
  mode; snapshot releases (`changeset version --snapshot pr123` +
  `changeset publish --tag pr123`) give per-PR test builds.
- semantic-release: channels come from `branches` config (`next` branch →
  `next` dist-tag, above).
- Fix a mistagged publish with `npm dist-tag add pkg@1.4.2 latest` — dist-tag
  moves are instant and don't republish.

## Routing

- Verifying provenance/signatures of dependencies you install, `npm audit
  signatures`, lockfile policy → `node-supply-chain`.
- `exports` maps, dual ESM/CJS builds, `files`/`publishConfig` contents,
  pack-and-inspect checks → `node-packaging`.
- Test/lint pipelines that gate the release workflow → `node-ci`.
