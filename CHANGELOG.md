# Changelog

All notable changes to this repository's skills are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versioning: [SemVer](https://semver.org) on the plugin manifest
(breaking skill-interface change → major, new skill → minor, fix → patch).

## [Unreleased]

## [0.3.0] - 2026-09-10

### Changed
- Currency pass against primary sources (2026-09-10): TypeScript 7.0 is GA and the
  regular `typescript` package (options 6.0 deprecated are hard errors on 7; nightlies
  moved to `typescript@next`); Vitest 5 is the current major (Node >= 22.12, Vite >= 6.4,
  `clearMocks` default, `test.sequential` removed); npm 12 is `latest` with
  `allowScripts` blocking dependency install scripts by default; pnpm 12 with
  `allowBuilds`/`strictDepBuilds`; npm trusted publishing allows up to 10 configs and
  defaults new ones to `npm stage publish` (2026-09-03); `changesets/action` v2 and
  `@changesets/cli` 3.x; GitHub Actions `checkout`/`setup-node` v7; Node 25 EOL;
  Dependabot's 3-day default cooldown (2026-07-14) and comment maintenance on SHA pins;
  yarn `npmMinimalAgeGate` default; Biome 2.5.12 and Next.js 16.3.x literals.
- `node-supply-chain/scripts/audit_supply_chain.py`: pnpm policy was inverted (a missing
  allowlist means scripts are *blocked* on pnpm >= 10, not "unconstrained"); recognises
  `allowBuilds`, flags `dangerouslyAllowAllBuilds`; npm >= 12 `allowScripts` policy;
  auto-merge detection ignores comment lines; `npm ci && npm install x` is still caught.
- `node-ci/scripts/check_workflows.py`: an `if: always()` job with no `needs.*.result`
  test is now an error (it was a silent pass), aggregators are judged per file,
  `on: [pull_request]` shorthand is detected, and odd/EOL Node lines (15-25) are flagged.
- `node-lint/scripts/check_lint_setup.py`: JSONC comment stripping no longer eats `//`
  inside strings (the `$schema` URL broke every biome.jsonc parse).
- `node-packaging/scripts/check_package.sh`: packs with the repo's own package manager
  (pnpm rewrites `workspace:` specifiers), accepts an existing tarball, pins publint and
  arethetypeswrong exactly, and no longer needs Python.
- `node-typescript` ratchet script no longer counts a broken `tsc` run as zero errors and
  makes baseline updates a human PR step; app template notes DOM/JSX libs.
- `node-release`: release-please + separate `release: published` publish chain only
  works with an App/PAT token (`GITHUB_TOKEN`-created releases trigger nothing); the
  minimal publish workflow now builds unconditionally, runs the packaging gate on the
  exact tarball, and pins npm.
- `node-packaging`: top-level `await` is an API decision, not a format decision;
  `nextjs-quality`: RSC boundary serialization lists what React actually supports.
- Descriptions: `node-testing` names Jest-to-Vitest migration; `nextjs-quality` says React
  Strict Mode and excludes tsconfig strictness and deploys. Rank-1 routing 89.0% -> 91.8%.
- Repo hooks: the bash guard now enforces the owner-only `git commit`/`git push` rule
  (any wrapper, `bash -c`, or newline), a Stop gate runs `make check` before a turn can end
  (with the `stop_hook_active` guard and a visible `systemMessage` release), the ruff pin
  is read from `requirements-dev.txt` instead of duplicated, the write-time validator also
  fires for `evals.json`/`references/` edits, and hook timeouts leave headroom.
- Validator: body length above 500 lines is an error; the ruff pin in
  `requirements-dev.txt`, `ruff.toml` and `.pre-commit-config.yaml` must agree.
- The rank-1 routing ratchet is armed (`--min-rank1 89`) in the Makefile and CI.
- `make check` now also runs the commit-stage hygiene hooks (`make hygiene`, converging on
  auto-fixes) and CI runs them once, failing on any modification — so the Stop gate and
  CI enforce the same gate `git commit` does (`detect-private-key` included).
- Bash guard: shell keywords (`if …; then git push`, `for …; do git commit`) no longer
  hide a git call; Stop gate: on the retry round it releases only when the failure
  output is unchanged (no progress), otherwise it keeps blocking up to the harness cap.
- `.pre-commit-config.yaml` comment: pre-commit itself fails a hook that modified files;
  `--exit-non-zero-on-fix` only matters for the same command run outside pre-commit.
- `docs/skill-authoring.md` and the validator's known frontmatter keys follow the current
  Claude Code skills reference (1,536-char listing truncation; `arguments`,
  `disallowed-tools`, `background`, `shell`, `compatibility`).
- From the research pass (primary sources cited in `.local/research`): npm 12's
  `strict-allow-scripts` is off by default (unapproved scripts are skipped and `npm ci`
  still passes — set it in CI), `.npmrc ignore-scripts=true` voids `allowScripts`, no Node
  line bundles npm 12 yet; pnpm 12 hard-fails on unknown workspace keys (a leftover
  `onlyBuiltDependencies` breaks the install) and `minimumReleaseAge` defaults to a day
  since 11.0; Yarn's upgrade migration writes the old no-gate default into existing
  projects; checkout v7's fork-PR guard was backported on 2026-07-20 and `issue_comment`
  jobs are the gap the 2026 attacks used; typescript-eslint has no TypeScript 7 support
  (pin lint-time TS to 6.x via the `typescript6` alias, or Oxlint + tsgolint); tsup 8.5.1
  breaks TS 6/7 declaration builds; tsdown's attw default profile changed; the Next.js
  lint codemod never touches CI and 16.3.3 disables AVIF inside a patch; `changesets/
  action` v2 requires CLI v3; semantic-release >= 25.0.9 for the un-advisoried
  argument-injection fix; bypass-2FA npm tokens lose direct publish ~Jan 2027; the keyv
  worm carried valid provenance and planted `.claude/settings.json` hooks — remove
  persistence before rotating credentials. The audit script warns when `.npmrc`
  `ignore-scripts=true` voids `allowScripts` and notes a missing `strict-allow-scripts`.

## [0.2.0] - 2026-08-31

### Added
- Adopted the current skillskit gate: executed trigger evals scoring every trigger
  prompt against every skill description (rank-1 routing accuracy 89.0%), a security
  scan over skill content and bundled scripts, ruff lint and format, README-shape
  validation, pre-commit hooks and a write-time lint hook.

### Changed
- Skill descriptions sharpened where the eval gate showed a sibling outranking a
  skill on its own trigger prompts, or a stated non-trigger matching better than any
  trigger. Fixes changed the scope boundary, not just the wording.

### Fixed
- Findings the new lint gate surfaced in this repo's own scripts, fixed at the
  source; where a rule was wrong for a line it is suppressed there with its reason.


### Added
- Eight Node-ecosystem skills: `node-lint`, `node-typescript`, `node-testing`,
  `node-packaging`, `node-release`, `node-ci`, `node-supply-chain`,
  `nextjs-quality` — each with trigger evals, a version-gated reference
  playbook, and deterministic verifier scripts where applicable.
- `docs/setup-prompt.md` — one-run orchestration prompt for applying the
  catalog to a target repo (write-surface-aware ordering).

### Added
- Repository scaffolded from the skills template.
