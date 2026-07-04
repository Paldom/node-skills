# Next.js App Router Quality Playbook

Scope: quality/setup of a Next.js **App Router** app — lint wiring, `next.config`
hardening, RSC/client boundary hygiene, bundle/image/font optimization, env
validation, and the build verification loop. Version-sensitive claims below are
current **as of mid-2026, Next.js 16.2.x** — re-verify against the linked
official docs before acting on them in a different major.

## Contents

- [Version context](#version-context)
- [Linting: `next lint` is gone — use the ESLint CLI](#linting-next-lint-is-gone--use-the-eslint-cli)
- [next.config hardening checklist](#nextconfig-hardening-checklist)
- [Output mode: match the deploy target](#output-mode-match-the-deploy-target)
- [RSC / client boundary hygiene](#rsc--client-boundary-hygiene)
- [Hydration-error causes checklist](#hydration-error-causes-checklist)
- [Bundle analysis and the real levers](#bundle-analysis-and-the-real-levers)
- [Image and font optimization checklist](#image-and-font-optimization-checklist)
- [Typed env validation](#typed-env-validation)
- [Verification loop](#verification-loop)
- [Out of scope — route to siblings](#out-of-scope--route-to-siblings)

## Version context

As of mid-2026 (verify: https://nextjs.org/docs/app/guides/upgrading/version-16):

- Current major is **Next.js 16** (16.2.x). Requires **Node.js >= 20.9** and
  **TypeScript >= 5.1**.
- **Turbopack is the default** for `next dev` and `next build`. A custom
  `webpack` config makes `next build` **fail**; opt out with `next build --webpack`
  or migrate the config to top-level `turbopack` options.
- Request APIs are **async-only**: `await cookies()`, `await headers()`,
  `await params`, `await searchParams`. No sync fallback remains.
- `middleware.ts` is deprecated in favor of `proxy.ts` (exported function
  `proxy`, Node.js runtime).
- `next build` output no longer prints per-route "First Load JS" sizes — use the
  bundle analyzer (below) instead.
- Upgrading a 15.x app: run `npx @next/codemod@canary upgrade latest` first.

## Linting: `next lint` is gone — use the ESLint CLI

As of Next.js 16, `next lint` and the `eslint` key in `next.config` are
**removed**, and `next build` **no longer runs linting**
(verify: https://nextjs.org/docs/app/api-reference/config/eslint).

- Install: `npm i -D eslint eslint-config-next`.
- Use **flat config** (`eslint.config.mjs`). `@next/eslint-plugin-next`
  defaults to flat config; ESLint v10 drops legacy `.eslintrc`.
- Migrate an old setup with `npx @next/codemod@canary next-lint-to-eslint-cli .`.
- Wire `"lint": "eslint ."` into `package.json` and CI yourself — nothing runs
  it for you anymore.

```js
// eslint.config.mjs
import { defineConfig, globalIgnores } from 'eslint/config'
import nextVitals from 'eslint-config-next/core-web-vitals'
import nextTs from 'eslint-config-next/typescript'

export default defineConfig([
  ...nextVitals, // base + Core Web Vitals rules as errors (recommended)
  ...nextTs,     // typescript-eslint recommended rules (TS projects)
  globalIgnores(['.next/**', 'out/**', 'build/**', 'next-env.d.ts']),
])
```

If the project already has conflicting `react`/`react-hooks`/`import` configs,
use `@next/eslint-plugin-next` directly instead of spreading `eslint-config-next`
(same doc, "Migrating existing config").

## next.config hardening checklist

Never rely on defaults that vary by version — state every option explicitly:

```ts
// next.config.ts
import type { NextConfig } from 'next'

const nextConfig: NextConfig = {
  // Default true in App Router since 13.5.1 — still set it explicitly.
  reactStrictMode: true,

  // Stable top-level option (formerly experimental.typedRoutes).
  // Types Link href + router.push/replace/prefetch. TS projects only.
  // Verify: https://nextjs.org/docs/app/api-reference/config/typescript
  typedRoutes: true,

  // Do NOT ship these true — they hide broken builds:
  typescript: { ignoreBuildErrors: false },

  images: {
    // images.domains is deprecated — use remotePatterns, as narrow as possible.
    remotePatterns: [{ protocol: 'https', hostname: 'images.example.com' }],
    // v16 defaults shown explicitly (they changed FROM v15 — pin them):
    qualities: [75],          // v15 allowed all; v16 default [75]
    minimumCacheTTL: 14400,   // v16 default 4h (was 60s)
    maximumRedirects: 3,      // v16 default 3 (was unlimited)
    dangerouslyAllowLocalIP: false, // never true outside private networks
    // Local images with query strings need localPatterns.search in v16.
  },

  // Only with a private error-reporting pipeline (see tradeoff below):
  productionBrowserSourceMaps: false,

  // Drop the X-Powered-By header.
  poweredByHeader: false,
}

export default nextConfig
```

- Image defaults changed in v16 (verify:
  https://nextjs.org/docs/app/guides/upgrading/version-16#nextimage-changes).
- `productionBrowserSourceMaps: true` gives readable client stack traces but
  **serves your source to anyone who asks**, and increases build time and
  memory (verify:
  https://nextjs.org/docs/app/api-reference/config/next-config-js/productionBrowserSourceMaps).
  Prefer uploading source maps privately to the error tracker; keep this `false`
  unless the app is open source.
- `serverRuntimeConfig`/`publicRuntimeConfig` are removed — use env vars.
- `next-env.d.ts`: on Next 16, **gitignore it** — the docs say "Add it to
  `.gitignore`. If your project already tracks the file, remove it from Git";
  it is regenerated by `next dev`/`next build`/`next typegen` (as of mid-2026,
  v16.2 docs; verify:
  https://nextjs.org/docs/app/api-reference/config/typescript#next-envdts).
  This is a Next 16-era docs change — Next <= 15 docs gave no such instruction
  and scaffolds conventionally committed the file, so follow your major's docs.
  If gitignored, any CI step that type-checks before a build must run
  `npx next typegen` first so the file exists.

## Output mode: match the deploy target

Verify: https://nextjs.org/docs/app/api-reference/config/next-config-js/output
and https://nextjs.org/docs/app/guides/static-exports

| Deploy target | `output` | Notes |
|---|---|---|
| Vercel / platform with a Next adapter | omit (default) | Platform handles tracing. |
| Docker / self-hosted Node | `'standalone'` | Emits `.next/standalone` + minimal `server.js`; copy `public/` and `.next/static/` in yourself (CDN-served ideally). Monorepo: set `outputFileTracingRoot`. |
| Static host / CDN only | `'export'` | Emits `out/`. No ISR, no Server Actions, no `cookies()`, no proxy/middleware, no rewrites/redirects/headers, no default image loader (needs `images.loader: 'custom'`), dynamic routes require `generateStaticParams()`. |

Choosing `'export'` for an app that later needs any server feature is a rewrite
trap — confirm the feature list before committing.

## RSC / client boundary hygiene

Verify: https://nextjs.org/docs/app/getting-started/server-and-client-components

- **Server by default.** Pages/layouts stay Server Components; fetch data
  there, close to the source, with secrets that never reach the client.
- **Minimal `'use client'` islands.** Put the directive on the smallest
  interactive leaf (button, search box), not on a layout or page. Everything a
  client file imports joins the client bundle.
- **Interleave via children.** Pass Server Components as `children`/props into
  client wrappers (modal, provider) — they stay server-rendered. Render context
  providers as deep as possible, wrapping `{children}` only.
- **Poisoning guards.** Add `import 'server-only'` at the top of every module
  that touches secrets or server-only APIs — importing it from a client module
  becomes a build error. Use `client-only` for `window`-touching modules.
  Installing the npm packages is optional (Next.js handles the imports
  internally) but do it if lint flags extraneous deps.
- **Props across the boundary must be serializable.** No functions, class
  instances, `Date`-typed surprises silently stringified — pass plain data.
- **No async client components** (`@next/next/no-async-client-component`
  catches this).

## Hydration-error causes checklist

When "hydration failed" appears, check in this order (verify:
https://nextjs.org/docs/messages/react-hydration-error):

1. Invalid HTML nesting: `<p>` inside `<p>`, `<div>` inside `<p>`, `<a>` in
   `<a>`, `<button>` in `<button>`.
2. `typeof window !== 'undefined'` branches in render logic.
3. Browser-only APIs (`window`, `localStorage`) read during render.
4. Time/locale-dependent output in render: `new Date()`, `Math.random()`,
   `toLocaleString()`.
5. Browser extensions mutating the DOM (reproduce in a clean profile).
6. Misconfigured CSS-in-JS or an HTML-rewriting CDN layer (e.g. auto-minify).

Fixes, in preference order: make server and client render identical → gate the
divergent part behind `useEffect` state → `next/dynamic` with `ssr: false` for
the one component → `suppressHydrationWarning` only for inevitable one-element
diffs like timestamps (one level deep, no text patching).

## Bundle analysis and the real levers

Two analyzers exist as of mid-2026 (verify:
https://nextjs.org/docs/app/guides/package-bundling):

- **Turbopack builds (the default):** `npx next experimental-analyze` —
  built-in interactive treemap with import-chain tracing, v16.1+, experimental
  (flag name may change; verify at use time). `--output` writes a static report
  to `.next/diagnostics/analyze` for before/after diffing.
- **Webpack builds only:** `@next/bundle-analyzer` — still documented, but it
  is a webpack plugin; pair it with `next build --webpack`:

```js
// next.config.js — webpack builds only
const withBundleAnalyzer = require('@next/bundle-analyzer')({
  enabled: process.env.ANALYZE === 'true',
})
module.exports = withBundleAnalyzer({ /* config */ })
// Run: ANALYZE=true next build --webpack
```

The levers that actually shrink bundles, in impact order:

1. **Move render-only work server-side.** Syntax highlighting, markdown, chart
   prep in a `'use client'` file ships the whole library; do it in a Server
   Component and send HTML/data instead.
2. **`next/dynamic` for conditional heavy UI** (modals, editors, admin panels)
   so they load on interaction, not first paint.
3. **Tree-shakeable imports.** For many-export packages (icons, utils) add
   `experimental.optimizePackageImports: ['pkg']` (experimental — verify:
   https://nextjs.org/docs/app/api-reference/config/next-config-js/optimizePackageImports;
   many popular libraries are auto-optimized already). Avoid barrel-file
   re-exports of heavy modules in your own code.
4. **`serverExternalPackages: ['pkg']`** for server-side packages that
   misbehave when bundled (native addons, large SDKs).

## Image and font optimization checklist

`next/image` (verify: https://nextjs.org/docs/app/api-reference/components/image):

- Use `next/image`, never raw `<img>` (`@next/next/no-img-element` enforces).
  `next/legacy/image` is deprecated — migrate imports.
- Always set `width`/`height` (or `fill` + sized parent) to prevent CLS.
- Preload the LCP image (usually the hero) and nothing else. On Next 16 the
  prop is `preload` — `priority` is **deprecated as of v16.0.0** (on Next 15
  and earlier, `priority` is the correct prop). The v16 docs add that in most
  cases `loading="eager"` or `fetchPriority="high"` is preferable to `preload`,
  e.g. when the LCP element varies by viewport.
- Set `sizes` on responsive/`fill` images so the browser picks a small source.
- Allowlist remote hosts via `images.remotePatterns` only, as narrowly as
  possible; review the v16 defaults pinned in the config block above.

`next/font` (verify: https://nextjs.org/docs/app/api-reference/components/font):

- Use `next/font/google` or `next/font/local` — fonts are self-hosted at build
  time; no runtime request to Google.
- Prefer **variable fonts**; otherwise specify `weight` explicitly.
- Always set `subsets: ['latin', ...]` (warns if missing while preloading) and
  `display: 'swap'` explicitly.
- Declare each font **once** in a definitions file (e.g. `app/fonts.ts`) and
  import the object — each loader call creates another hosted instance.
- Integrate with Tailwind/CSS via the `variable: '--font-x'` option, applied on
  `<html>` in the root layout.

## Typed env validation

Fail fast on missing/malformed env instead of debugging `undefined` at runtime.
Hand-rolled pattern with zod (any schema lib works):

```ts
// lib/env.server.ts — server-only values
import 'server-only'
import { z } from 'zod'

export const env = z
  .object({
    DATABASE_URL: z.string().url(),
    API_KEY: z.string().min(1),
  })
  .parse(process.env) // throws with a readable report at first server import
```

```ts
// lib/env.client.ts — NEXT_PUBLIC_ values are inlined at BUILD time,
// so each one must be referenced statically; z.parse(process.env) alone
// cannot see them in the browser.
import { z } from 'zod'

export const clientEnv = z
  .object({ NEXT_PUBLIC_API_URL: z.string().url() })
  .parse({ NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL })
```

- Trigger server validation at boot by importing `lib/env.server` from
  `instrumentation.ts` `register()` (verify:
  https://nextjs.org/docs/app/guides/instrumentation).
- Do **not** import a `server-only` module from `next.config.ts` — the config
  file runs outside the bundler and the guard throws there.
- Optional editor autocomplete for env keys: `experimental.typedEnv: true`
  (experimental as of 16.2 — verify:
  https://nextjs.org/docs/app/api-reference/config/typescript).
- Libraries like `@t3-oss/env-nextjs` package this pattern — evaluate at use
  time.

## Verification loop

After **every** config or boundary change, run the full gate — no exceptions:

1. `npx next build` — must pass. It type-checks (build fails on TS errors) but
   does **not** lint in v16.
2. `npx eslint .` — must pass (lint is now your job, see above).
3. If routes/params changed: `npx next typegen` regenerates `PageProps` /
   `LayoutProps` / `RouteContext` helpers without a full build.
4. For bundle-affecting changes: `npx next experimental-analyze --output`
   before and after; diff `.next/diagnostics/analyze`.
5. Smoke the changed routes with `next start` (not just `next dev` — dev masks
   prod-only behavior like caching and image optimization).

Treat a red `next build` as a stop-the-line event: fix before the next edit so
failures stay attributable to one change.

## Out of scope — route to siblings

- Generic ESLint/Prettier rules beyond `eslint-config-next` → `node-lint`.
- tsconfig strictness policy, TS project setup → `node-typescript`.
- Test runner setup (Vitest/Playwright etc.), even for Next apps → `node-testing`.
- CI pipeline wiring for the commands above → `node-ci`.
- Publishing/packaging libraries (including `use client` in shipped libs'
  bundler config) → `node-packaging`.
- Dependency pinning/audit policy → `node-supply-chain`.
- Deployment platform specifics (Vercel settings, Dockerfiles, CDNs): out of
  scope for this skill entirely.
