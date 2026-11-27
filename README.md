# Mini-CRM

[![CI](https://github.com/vidalicaro-byte/mini-crm/actions/workflows/ci.yml/badge.svg)](https://github.com/vidalicaro-byte/mini-crm/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

🇺🇸 English · [🇧🇷 Português](README.pt-BR.md)

A sales CRM front end: a dashboard with KPIs and charts, searchable contact and company lists, and a kanban funnel you can drag deals across — with roles, light/dark themes and a mobile layout. The live demo runs on a **real REST API** ([mini-crm-api](https://github.com/vidalicaro-byte/mini-crm-api): FastAPI + PostgreSQL); locally it can also run on a **simulated API inside the browser**, with no backend at all.

**[▶ Live demo](https://mini-crm-ten-coral.vercel.app/)** — click "Entrar como administradora" (administrator) or "Entrar como vendedor" (seller) on the login page. The interface is in Brazilian Portuguese. The demo API sleeps when idle (free hosting), so the first visit may show a short "waking up the server" screen; the demo data is reset every night.

|                                                  |                                                    |
| ------------------------------------------------ | -------------------------------------------------- |
| ![Overview](docs/screenshots/overview-dark.png)  | ![Funnel](docs/screenshots/pipeline-dark.png)      |
| ![Contacts](docs/screenshots/contacts-light.png) | ![Companies](docs/screenshots/companies-light.png) |

<p>
  <img src="docs/screenshots/mobile-overview-dark.png" alt="Overview on a phone" width="260">
  <img src="docs/screenshots/mobile-pipeline-dark.png" alt="Funnel on a phone" width="260">
  <img src="docs/screenshots/company-light.png" alt="Company page" width="420">
</p>

## What it does

- **Sign in with roles.** An _administrator_ sees everything; a _seller_ only sees their own contacts and deals (the API enforces it, not just the screens). Only the administrator gets the team page.
- **Overview.** Five KPIs (contacts, new contacts, open deals, won revenue, conversion rate) compared with the previous period, a deals-by-stage chart and a revenue-over-time chart. A period filter (7 days, 30 days, 90 days, 12 months) lives in the URL. Each chart has a text summary and its data as a table.
- **Contacts.** Server-side search, company filter, sorting and pagination, all kept in the URL (shareable links, working Back button). Detail page with deals and activity history; create and edit with validation in Portuguese.
- **Companies.** The same list tools plus a size filter; the detail page shows contacts, open deals and a summary. Figures count only what the signed-in user may see.
- **Funnel.** A kanban board: drag a deal between stages with the mouse, with touch, or with the keyboard, or use each card's "Mover" menu. The card moves at once and is put back, with an explanation, if the server refuses.
- **Everywhere:** light and dark themes, responsive layout, loading skeletons, and error and empty states with a retry.

## Engineering notes

- **One contract, two backends.** Every response is parsed with [Zod](https://zod.dev/) schemas (`src/api/schemas.ts`). In development and tests, [MSW](https://mswjs.io/) serves that contract with realistic latency, validation (`422`), conflicts (`409`), `401` and `403`. In production the same screens talk to [a real API](https://github.com/vidalicaro-byte/mini-crm-api) that implements it: switching was a matter of environment variables, not screen changes.
- **Cold starts handled.** Free hosting puts the API to sleep; a gate polls its health check and, if the wait is noticeable, explains it instead of showing a wall of spinners, with a retry if the server never answers.
- **Server state with TanStack Query**: query keys per list, `keepPreviousData` while paging, invalidation after writes (a new contact updates the overview and the company figures), and an optimistic update with per-card rollback on the funnel.
- **The URL is the state of a list.** Pure functions parse and write the filters (unit-tested, including invalid and hand-edited URLs); one hook serves both the contacts and the companies lists.
- **Accessibility is tested, not hoped for.** [axe](https://github.com/dequelabs/axe-core) runs on every page in light and dark themes, on desktop and phone, in CI. It found real problems along the way (list markup, a control whose name differed from its visible text, low-contrast labels), now fixed. The funnel works by keyboard with announcements in Portuguese, and the app has a skip link and moves focus on navigation.
- **Performance.** Routes load on demand, the charts load after the numbers, and the mock layer's bundle was cut from 521 kB to 251 kB by stubbing an unused dependency in production builds.

### Quality

| What                                  | How                                                                                                                                            |
| ------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| 255 unit and integration tests        | [Vitest](https://vitest.dev/) + Testing Library, with the mock API running underneath                                                          |
| 75 end-to-end and accessibility tests | [Playwright](https://playwright.dev/) + axe against the production build, desktop and phone profiles                                           |
| Static checks                         | TypeScript (strict, `noUncheckedIndexedAccess`), [oxlint](https://oxc.rs/docs/guide/usage/linter) (with jsx-a11y rules), Prettier              |
| Git hygiene                           | Husky + lint-staged, [Conventional Commits](https://www.conventionalcommits.org/) with commitlint, squash merges                               |
| CI                                    | GitHub Actions runs the checks and the end-to-end tests on every pull request, and `main` is protected; Dependabot proposes dependency updates |

### Lighthouse

Median of 3 runs per page with `npm run lighthouse` (headless Chrome, production build; the phone profile uses Lighthouse's simulated slow 4G and a 4× slower CPU).

| Profile | Page     | Performance | Accessibility | Best practices | SEO | LCP   | TBT    | CLS   |
| ------- | -------- | ----------- | ------------- | -------------- | --- | ----- | ------ | ----- |
| phone   | Login    | 92          | 100           | 100            | 100 | 0.8 s | 339 ms | 0.000 |
| phone   | Overview | 90          | 100           | 100            | 100 | 1.8 s | 400 ms | 0.000 |
| phone   | Contacts | 86          | 100           | 100            | 100 | 1.9 s | 524 ms | 0.000 |
| phone   | Funnel   | 83          | 100           | 100            | 100 | 1.7 s | 675 ms | 0.000 |
| desktop | Login    | 100         | 100           | 100            | 100 | 0.3 s | 13 ms  | 0.000 |
| desktop | Overview | 100         | 100           | 100            | 100 | 0.6 s | 16 ms  | 0.000 |
| desktop | Contacts | 100         | 100           | 100            | 100 | 0.6 s | 14 ms  | 0.000 |
| desktop | Funnel   | 100         | 100           | 100            | 100 | 0.6 s | 72 ms  | 0.000 |

Numbers vary by machine; run the command to measure on yours.

## Tech stack

React 19 · TypeScript · Vite · Material UI (with MUI X Data Grid and Charts) · React Router · TanStack Query · React Hook Form + Zod · dnd-kit · MSW · Vitest · Playwright · Deployed on Vercel, with the [API](https://github.com/vidalicaro-byte/mini-crm-api) on Render.

## Running it locally

Requires Node.js 24 or newer.

```bash
git clone https://github.com/vidalicaro-byte/mini-crm.git
cd mini-crm
npm install
npm run dev
```

Open http://localhost:5173. Demo accounts (also one click on the login page):

| Role          | E-mail                | Password   |
| ------------- | --------------------- | ---------- |
| Administrator | `marina@minicrm.demo` | `demo1234` |
| Seller        | `rafael@minicrm.demo` | `demo1234` |

| Command                                          | What it does                                                          |
| ------------------------------------------------ | --------------------------------------------------------------------- |
| `npm run dev`                                    | Dev server                                                            |
| `npm run build` / `npm run preview`              | Production build / serve it locally                                   |
| `npm test`                                       | Unit and integration tests                                            |
| `npx playwright install chromium`, `npm run e2e` | Download the test browser once, then run the end-to-end and axe tests |
| `npm run lighthouse`                             | Build, serve and measure with Lighthouse                              |
| `npm run lint` · `typecheck` · `format:check`    | Static checks                                                         |
| `npm run seed`                                   | Regenerate the fake data (`src/mocks/seed.json`)                      |

By default everything runs on the in-browser mock API. To use the real API instead (running locally, see its README), create `.env.local`:

```bash
VITE_ENABLE_MOCKS=false
VITE_API_URL=http://localhost:8000/api
VITE_DEMO_ACCOUNTS=true   # keep the one-click demo sign-in buttons
```

## Project layout

```
src/
  api/          HTTP client and Zod schemas (the contract)
  app/          routes, layout, navigation
  components/   shared pieces (page header, search field, detail sections)
  features/     one folder per area: auth, dashboard, contacts, companies, pipeline, deals, team
  hooks/        useUrlFilters
  mocks/        the in-browser API: handlers, seed data, authorization, overview maths
  theme/        light and dark themes
e2e/            Playwright tests
```

## Limitations

- The data is fake. On the live demo it is shared by every visitor and reset every night; on the mock API it lives in the browser's memory and **reloading the page resets it**.
- The interface is Brazilian Portuguese only; there is no translation layer.
- Companies and deals are read-only in the interface (contacts can be created and edited; deals move between stages).

## License

[MIT](LICENSE)
