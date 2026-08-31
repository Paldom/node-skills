# Changelog

All notable changes to this repository's skills are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versioning: [SemVer](https://semver.org) on the plugin manifest
(breaking skill-interface change → major, new skill → minor, fix → patch).

## [Unreleased]

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
