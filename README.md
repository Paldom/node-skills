# Node Skills

[![CI](https://github.com/Paldom/node-skills/actions/workflows/ci.yml/badge.svg)](https://github.com/Paldom/node-skills/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![skills.sh](https://skills.sh/b/Paldom/node-skills)](https://skills.sh/Paldom/node-skills)

Agent Skills for maintaining high-quality open-source Node.js, TypeScript, Next.js, and React apps and packages - linting, type safety, testing, packaging and releases, and CI quality gates.

Agent Skills for [Claude Code](https://code.claude.com/docs/en/skills) (and any
[Agent Skills](https://agentskills.io)-compatible tool). Each skill is a folder under
[`skills/`](skills/) with a single-purpose `SKILL.md`, trigger evals, and optional
scripts/references — validated on every write, commit, and PR.

## Quick start

Install with the [skills CLI](https://skills.sh) — auto-detects 70+ agents
(Claude Code, Codex, Cursor, Copilot, pi, …):

```bash
npx skills add Paldom/node-skills                  # all detected agents
npx skills add Paldom/node-skills -a codex -a pi   # or target specific agents
```

Or with the [GitHub CLI](https://cli.github.com/manual/gh_skill_install) (≥ 2.90),
including version-pinned installs from releases:

```bash
gh skill install Paldom/node-skills
gh skill install Paldom/node-skills <skill> --pin <tag>
```

Or as a Claude Code plugin:

```
/plugin marketplace add Paldom/node-skills
/plugin install node-skills@node-skills
```

Or copy a single skill into a project:

```bash
git clone https://github.com/Paldom/node-skills.git
cp -r node-skills/skills/<skill-name> your-project/.claude/skills/
```

Then just describe the task — the skill activates on its description — or invoke it
explicitly with `/<skill-name>`.

To bring a whole repository up to the quality bar in one run, paste the
[setup prompt](docs/setup-prompt.md) — it applies the catalog in
write-surface-safe order (parallel where safe, sequential where skills share
`package.json`) with verifier gates and a single reviewed commit.

## Skills

| Skill | Description |
| --- | --- |
| [node-lint](skills/node-lint/) | Linting and formatting — Biome one-tool or ESLint flat config + Prettier, migrations, rule tuning, CI wiring. |
| [node-typescript](skills/node-typescript/) | Explicit strict tsconfig — module/resolution by consumption model, declaration emit, type-check gates, incremental strictification. |
| [node-testing](skills/node-testing/) | Vitest or node:test with explicit config — v8 coverage gates that fail CI, React Testing Library, mocking discipline. |
| [node-packaging](skills/node-packaging/) | npm package artifacts — exports maps, ESM-first vs dual decisions, tsdown bundling, publint + arethetypeswrong gates. |
| [node-release](skills/node-release/) | Release automation — Changesets or semantic-release, npm trusted publishing (OIDC) with provenance, first-publish bootstrap. |
| [node-ci](skills/node-ci/) | GitHub Actions CI — engines-derived matrices, caching, pnpm without corepack, fail-closed aggregator, merge_group. |
| [node-supply-chain](skills/node-supply-chain/) | npm supply-chain hardening — lockfile discipline, Dependabot cooldown limits, per-PM install-script policy, SHA pinning. |
| [nextjs-quality](skills/nextjs-quality/) | Next.js App Router quality — next.config hardening, Next-native lint, RSC boundary hygiene, measured bundle optimization. |

## Repository structure

```
skills/                  # distributed skills, one folder per skill (SKILL.md + evals/ + scripts/)
docs/                    # skill-authoring guide, eval methodology, deployment guide
scripts/                 # deterministic validator used by hooks and CI
skills.sh.json           # skills.sh repo-page customization (groupings)
.claude/                 # agentic dev setup: hooks + bundled add-skill / publish-repo skills
.claude-plugin/          # plugin + marketplace manifests (makes this repo installable)
.local/                  # gitignored working area: sources, research, PROMPT.md (see below)
```

## Working on this repo with an agent

This repo is agent-native: canonical agent instructions live in
[AGENTS.md](AGENTS.md) (CLAUDE.md imports it), hooks validate every `SKILL.md` on
write, `make check` runs the full validator, and CI enforces the same gate on every
PR. The bundled `add-skill` skill walks the eval-first authoring workflow described
in [docs/skill-authoring.md](docs/skill-authoring.md). Maintainers drive sessions
with their own (gitignored, personal) `.local/PROMPT.md` goal prompt.

## Contributing

Contributions welcome — see [CONTRIBUTING.md](CONTRIBUTING.md) for the skill-proposal
process, the authoring workflow, and the PR checklist. Please note the
[Code of Conduct](CODE_OF_CONDUCT.md).

## Support

Questions, ideas, or something not working? Start with [SUPPORT.md](SUPPORT.md) —
bugs and skill proposals have [issue templates](../../issues/new/choose), and
security concerns go through [SECURITY.md](SECURITY.md) (never a public issue).

## License

[MIT](LICENSE) © 2026 Paldom
