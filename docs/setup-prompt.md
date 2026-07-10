# Setup prompt — Node-ecosystem quality setup in one run

A paste-ready `/goal` prompt that applies this catalog to a target repo. Four
skills write to `package.json`, so ordering is write-surface-aware: disjoint
work runs in parallel, `package.json`-touching skills run sequentially, and
CI/release wire everything last.

## Prerequisites (once per target repo)

```
/plugin marketplace add Paldom/node-skills
/plugin install node-skills@node-skills
```

or `npx skills add Paldom/node-skills -a claude-code`. The CI/release steps
need an authenticated `gh` CLI.

## The prompt

Open Claude Code at the target repo's root and paste:

```
/goal Bring this repo up to the node-skills quality bar: detect its shape, apply the relevant skills in write-surface-safe order, verify every gate. Never run git commit or git push - all changes stay in the working tree for my review. Work autonomously; stop only for decisions that are mine (publishing, deleting, visibility).

Prerequisites (verify first; stop and tell me if missing): node-skills skills resolve (try /node-lint); gh CLI authenticated; clean git status at repo root.

Phase 0 - SHAPE (read-only): detect package manager (lockfile), package.json engines, repo kind: published library, Next.js app, other app, or monorepo. Record a baseline: current lint/type/test/build commands and pass/fail. Shape decides applicability: libraries get node-packaging + node-release; Next.js apps get nextjs-quality (skip packaging/release unless it also publishes packages).

Phase 1 - PARALLEL (disjoint surfaces, two subagents; name the skill explicitly in each subagent's instructions; nobody runs git):
   - Agent A -> /node-typescript: explicit tsconfig for the repo's consumption model + type-check gate. Owns tsconfig* only; package.json script additions are REPORTED back, not written.
   - Agent B -> /node-supply-chain: lockfile/CI-install discipline, dependabot.yml with cooldown+groups, per-package-manager install-script policy, SHA-pin third-party actions. Owns .github/dependabot.yml, .npmrc/.yarnrc.yml/pnpm fields, workflow pin fixes. Must finish with audit_supply_chain.py clean or dispositioned.
Phase 2 - SEQUENTIAL package.json chain (all edit package.json - never parallelize):
   1. /node-lint (configs + lint/format scripts; check_lint_setup.py clean),
   2. /node-testing (runner config + coverage gate; prove the gate fails once),
   3. libraries only: /node-packaging (exports map, format decision from engines, files whitelist; check_package.sh clean),
   4. Next.js apps only: /nextjs-quality (next.config hardening, Next-native lint, boundary fixes; next build green).
   Fold in the script additions Agent A reported.
Phase 3 - WIRING (after 1-2, sequential):
   - /node-ci: engines-derived matrix, caching, fail-closed aggregator, merge_group; workflows must pass check_workflows.py AND Agent B's pinning rules.
   - published libraries: /node-release: trusted publishing (OIDC) with the first-publish bootstrap stated; do NOT publish anything in this run.
Phase 4 - VERIFY: re-run every skill's verifier script + lint, type-check, test with coverage, build. Produce a baseline -> after table; list anything skipped with its reason.
Phase 5 - HANDOFF: leave everything uncommitted; present the before/after table and changed-file list. Never run git commit or git push.

Definition of Done:
- Every applicable skill applied, verifier green (or findings dispositioned in writing)
- lint + type-check + test + build pass locally; coverage gate proven to fail when unmet
- CI workflows schema-valid, fail-closed, supply-chain compliant
- No package.json merge artifacts (the sequential chain is why)
- All changes uncommitted, with the before/after summary and file list reported
```

## Notes

- Drop phases that don't apply: pure libraries skip `nextjs-quality`; apps that
  never publish skip `node-packaging`/`node-release`. E2E testing is a non-goal.
- The `package.json` chain is the one hard ordering rule.
