# Setup prompt — Node-ecosystem quality setup in one run

A paste-ready `/goal` prompt that applies this catalog to a target repo. Unlike
fully-parallel orchestrations, **four of these skills write to `package.json`**
(scripts/fields), so the ordering below is write-surface-aware: truly disjoint
work runs in parallel, `package.json`-touching skills run as a sequential chain,
and CI/release wire everything last.

## Prerequisites (once per target repo)

```
/plugin marketplace add Paldom/node-skills
/plugin install node-skills@node-skills
```

or `npx skills add Paldom/node-skills -a claude-code`. You also need an
authenticated `gh` CLI for the CI/release steps.

## The prompt

Open Claude Code at the target repo's root and paste:

```
/goal Bring this repository up to the node-skills quality bar - detect its shape, apply the relevant skills in write-surface-safe order, verify every gate, and finish with a single reviewed commit. Work autonomously; stop only for decisions that are genuinely mine (publishing, deleting, visibility).

Prerequisites (verify first; stop and tell me if missing):
- The node-skills skills resolve in this session (try /node-lint). gh CLI authenticated. Clean git status at the repo root.

Phase 0 - SHAPE (read-only): determine package manager (lockfile), package.json engines, repo kind: published library, Next.js app, other app, or monorepo. Record a baseline: current lint/type/test/build commands and their pass/fail state. The shape decides which skills apply: libraries get node-packaging + node-release; Next.js apps get nextjs-quality (and skip packaging/release unless it also publishes packages).

Phase 1 - PARALLEL (disjoint surfaces, two subagents; name the skill explicitly in each subagent's instructions; no subagent commits):
   - Agent A -> /node-typescript: explicit tsconfig for the repo's consumption model + type-check gate. Owns tsconfig* only; package.json script additions are REPORTED back, not written.
   - Agent B -> /node-supply-chain: lockfile/CI-install discipline, dependabot.yml with cooldown+groups, per-package-manager install-script policy, SHA-pin third-party actions. Owns .github/dependabot.yml, .npmrc/.yarnrc.yml/pnpm fields, workflow pin fixes. Must finish with its audit_supply_chain.py clean or dispositioned.
Phase 2 - SEQUENTIAL package.json chain (these all edit package.json - never parallelize them):
   1. /node-lint (configs + lint/format scripts; run check_lint_setup.py clean),
   2. /node-testing (runner config + coverage gate that fails; prove the gate fails once),
   3. libraries only: /node-packaging (exports map, format decision from engines, files whitelist; run check_package.sh clean),
   4. Next.js apps only: /nextjs-quality (next.config hardening, Next-native lint, boundary fixes; next build green).
   Fold in the script additions Agent A reported.
Phase 3 - WIRING (after 1-2, sequential):
   - /node-ci: engines-derived matrix, caching, fail-closed aggregator, merge_group; workflows must pass check_workflows.py AND the supply-chain pinning rules from Agent B.
   - libraries being published: /node-release: trusted publishing (OIDC) setup with the first-publish bootstrap stated; do NOT publish anything in this run.
Phase 4 - VERIFY: re-run every skill's verifier script + the full command set (lint, type-check, test with coverage, build). Produce a baseline -> after table. Anything intentionally skipped is listed with its reason.
Phase 5 - COMMIT: one orchestrator commit (owner's git identity, no AI mentions in the message), summarizing the before/after table. Push only if the branch tracking is already set up; otherwise leave the commit local and say so.

Definition of Done:
- Every applicable skill applied with its verifier green (or findings dispositioned in writing)
- lint + type-check + test + build all pass locally; coverage gate proven to fail when unmet
- CI workflows schema-valid, fail-closed, supply-chain compliant
- No package.json merge artifacts (the sequential chain is why)
- Single clean commit with the before/after summary
```

## Notes

- Drop phases that don't apply: a pure library skips `nextjs-quality`; an app
  that never publishes skips `node-packaging`/`node-release`.
- E2E/browser testing is an explicit non-goal of this catalog — bring Playwright
  separately.
- The `package.json` chain is the one hard ordering rule; everything else can be
  reshuffled if a phase is irrelevant.
