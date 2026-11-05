# EUNOMIA site

The deployment site: the documentation and its landing page, for people who run EUNOMIA. Built with [Fumadocs](https://fumadocs.dev) on Next.js and exported as a static site. Published by [`.github/workflows/docs.yml`](../.github/workflows/docs.yml) to <https://eunomiaupm.github.io/eunomia-deployment>.

```bash
npm ci
npm run dev            # http://localhost:3000, with hot reload
npm run build          # static export in out/
npm run generate:api   # regenerate content/docs/api/ after an OpenAPI spec changes
npm run types:check
```

## Where things are

| Path | What |
| --- | --- |
| `content/docs/` | The documentation, one MDX file per page; `meta.json` files order the sidebar |
| `content/docs/api/` | Generated from the OpenAPI specs: do not edit, run `npm run generate:api` |
| `content/docs/cli/reference.mdx` | Generated from the CLI: run `python3 cli/tools/gen_cli_docs.py` from the repo root |
| `app/(home)/page.tsx` | The landing page |
| `lib/site.ts` | Site facts: name, links, components, standards |
| `components/landing/` | Landing building blocks: sections, headings, terminal, marquee |
| `components/diagrams.tsx` | The architecture diagrams used in the docs and on the landing page |
| `app/global.css` | Theme: brand colours, light and dark tokens, landing utilities |
| `public/brand/` | Logos |

## Conventions

- This site is technical: the project itself, its team and its events belong to the project website ([eunomia.dit.upm.es](https://eunomia.dit.upm.es)). `cli/tests` checks no event page comes back.
- Pages link to each other with absolute paths (`/docs/...`) and to repository files with GitHub URLs.
- Diagrams are inline SVG using the theme tokens, so they work in light and dark mode.
- For GitHub Pages the site is built with `NEXT_PUBLIC_BASE_PATH=/eunomia-deployment`; images under `public/` go through `asset()` from `lib/site.ts`.
