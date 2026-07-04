---
name: nextjs-quality
description: Tunes Next.js App Router application quality - next.config hardening, eslint-config-next flat config, strict mode and typed routes, RSC and use-client boundary hygiene, bundle analysis, image and font optimization. Use when the user asks to production-harden a Next.js app, fix hydration or use-client errors, or shrink a Next bundle. Not for generic Node linting, unit test setup, or npm packaging.
license: MIT
argument-hint: [harden|boundaries|bundle]
---

# nextjs-quality

Applies App-Router-era Next.js quality practice — where generic Node advice and
pages-router folklore actively mislead. The failures this skill fixes: models
sprinkle `use client` until errors stop, configure generic ESLint instead of the
Next ruleset, quote deprecated `next lint`-era workflows, and "optimize" bundles
without measuring.

## When NOT to use

- Generic Node/TS lint outside a Next app → `node-lint`.
- Unit/component test setup → `node-testing`.
- Packaging a library → `node-packaging`; deploys/hosting → out of scope.
- Writing app features → ordinary dev work.

## Workflow

1. **Audit current state**: Next major (the playbook version-gates what's
   stable vs experimental per line), `next.config.*`, lint setup, `next build`
   output as the baseline.
2. **Lint the Next way**: `eslint-config-next` in flat config (the playbook has
   the current wiring — verify the `next lint` deprecation state for the
   installed major); its RSC/boundary rules are the point, don't swap them for
   generic configs.
3. **next.config hardening** from the playbook checklist: `reactStrictMode`,
   typed routes (status verified per version), images config, `output` mode
   matched to the deploy target, source-map policy — each explicit, none by
   default-trust.
4. **Boundary hygiene** (the hydration / `use client` complaint): find the
   actual offending imports; make client islands minimal; keep data fetching
   and secrets server-side (`server-only` where it protects); add the lint
   rules that catch regressions. Playbook has the common-causes checklist.
5. **Bundle work is measurement work**: analyzer first, then the real levers —
   dynamic imports, server components for static parts, tree-shakeable imports,
   `next/image` + `next/font` — and re-measure; report the delta, not vibes.
6. **Verify after every change**: `next build` green is the loop gate; type and
   lint gates stay on.

## Output spec

An explicit hardened `next.config`, Next-native lint in force, no unexplained
`use client` at module tops, measured bundle deltas for optimization asks, and
`next build` passing — with anything version-experimental labeled as such.

## Gotchas

- `use client` marks a boundary, not a fix — adding it at the top of a big tree
  ships the tree to the client; islands, not blankets.
- Hydration mismatches are usually non-deterministic render inputs (dates,
  random, locale) — the checklist finds them faster than console archaeology.
- `output: 'export'` silently disables server features — deploy target first,
  config second.
- Next majors move fast: the playbook version-gates typed-routes/lint specifics;
  re-verify against nextjs.org docs for the installed major.

## Files

- `references/nextjs-playbook.md` — version-gated config checklist, flat-config
  lint wiring, boundary/hydration checklists, bundle levers, env validation.
