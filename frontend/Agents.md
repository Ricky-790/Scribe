# Scribe — Frontend Implementation Guide

You are implementing the production React frontend for **Scribe**, an AI research
assistant. Your job is to turn the design into a working, correctly-wired React
application.

> **Note (2026-09):** this project was renamed from *Spectator* to *Scribe*, and
> the visual design was rebuilt from scratch. The original Material-Design
> amber-on-near-black system and the static HTML references in
> `stitch_spectator_research_platform_ui/` are **historical** — they no longer
> describe what ships. See "Design system" below for the current one. The
> backend contract described further down this file is unchanged and still
> authoritative.

## Stack

- **React** (Vite), functional components + hooks only. No class components.
- **React Router** for the 5 routes listed below.
- **Tailwind CSS** with custom color tokens exposed as CSS custom properties.
- **Fonts**: "Source Serif 4" (headings, report content) and "Inter" (UI chrome)
  via Google Fonts, plus "JetBrains Mono" for log/code output and "Material
  Symbols Outlined" for icons — all referenced in `index.html`.
- Plain `fetch` (or a small wrapper) for HTTP calls, native `WebSocket` for streaming.
  No need for a heavy data-fetching library — this app's data needs are simple.
- Store the JWT in `localStorage`. Attach it as `Authorization: Bearer <token>` on every
  request except signup/signin.

## Design system

Two themes driven by `data-theme` on `<html>`: `"paper"` (warm off-white, the
default) and `"ink"` (low-light). The choice persists in `localStorage` under
`scribe-theme` and is resolved before first paint by an inline script in
`index.html`, so there is no flash of the wrong palette. The full token values
live at the top of `src/index.css`; every Tailwind colour resolves through them,
so **never hardcode a hex in a component** — add or change a token instead.

Roles, in order of importance:

| Role           | Purpose                                              |
| -------------- | ---------------------------------------------------- |
| `primary`      | Ink itself. Buttons, structure. Not a colour.        |
| `accent`       | The single colour moment: burnt sienna. Links, the in-progress state, focus rings. |
| `secondary`    | Forest green. "Complete" only.                       |
| `tertiary`     | Deep teal. Rare, structural only.                    |
| `error`        | Brick. Failures only.                                |

Constraints worth keeping — these are deliberate, not oversights:

- **No drop shadows.** Separation comes from hairlines and tonal steps.
- **No `backdrop-blur` / glassmorphism.** Sticky bars are solid with a border.
- **Tight radii** (4–8px on containers). Pills are reserved for status/meta tags.
- **A small motion budget.** Entrance animation is for the hero only; everything
  else that moves is either live state (progress, spinners, streaming) or a
  functional transition. `prefers-reduced-motion` disables all of it.

## Design reference

The five static HTML exports in `stitch_spectator_research_platform_ui/` predate
the redesign. They remain useful only as a record of the original information
architecture. Map of old reference → route:

| Reference folder              | Route                                                        |
| ----------------------------- | ------------------------------------------------------------ |
| `landing_page`                | `/`                                                          |
| `signup_page`                 | `/signup` (adapt the same visual treatment for `/login`)     |
| `chat_page`                   | `/chat`                                                      |
| `research_report_in_progress` | `/report/:reportId` (in-progress state)                      |
| `research_report_completed`   | `/report/:reportId` (completed state)                        |

## Routes to implement

1. `/` — Landing page. Public.
2. `/signup` — Signup form. Public. Redirect to `/chat` if already authenticated.
3. `/login` — Login form. Public. Redirect to `/chat` if already authenticated.
4. `/chat` — Main research input. Protected (requires auth).
5. `/report/:reportId` — Report detail, live progress + final content. Protected.

Any protected route without a valid token in `localStorage` redirects to `/login`.

## Backend

Base URL for all HTTP calls: `http://localhost:8000`
Base URL for the WebSocket: `ws://localhost:8000`

Do not hardcode this string in more than one place — put it in a single config
constant (e.g. `src/config.js`) so it can be changed later without a find-and-replace.

### Auth endpoints

**`POST /auth/signup`**
Request body:

```json
{ "username": "string", "email": "string", "password": "string" }
```

Response body:

```json
{ "access_token": "string" }
```

On success, store `access_token` in `localStorage` and navigate to `/chat`.

**`POST /auth/signin`**
Request body:

```json
{ "email": "string", "password": "string" }
```

Response body: same shape as signup, `{ "access_token": "string" }`.
On success, store the token and navigate to `/chat`.

Both endpoints return a 4xx with a JSON body containing a `detail` string on failure
(e.g. wrong password, duplicate email) — display `detail` as the form's error message.

### Chat endpoint

**`POST /chat`** — requires `Authorization: Bearer <token>`
Request body:

```json
{ "query": "string" }
```

Response body:

```json
{
  "message": "string",
  "intent": "greeting" | "research_topic" | "unsupported",
  "report_id": "string (uuid) | null"
}
```

Behavior:

- If `report_id` is `null` (intent was `greeting` or `unsupported`), display `message`
  directly on the `/chat` page as a single quiet reply — do not navigate anywhere.
- If `report_id` is present (intent was `research_topic`), navigate immediately to
  `/report/{report_id}`.

### Reports endpoints

**`GET /reports/reports`** — requires auth. List the current user's past reports for
the sidebar.
Response body:

```json
{
  "reports": [
    {
      "report_id": "string (uuid)",
      "title": "string | null",
      "status": "string | null"
    }
  ],
  "limit": 0,
  "offset": 0
}
```

Notes:

- `title` is `null` until the report reaches the synthesis stage — render a placeholder
  label (e.g. "Untitled report") in that case, not a blank row.
- `status` is one of: `pending`, `planning`, `researching`, `synthesizing`, `done`,
  `failed` (also possibly `null` — treat `null` the same as an unknown/in-progress
  state). Use this to render the sidebar's status indicator per the design reference
  (amber pulse = in progress, sage/success = done, terracotta/error = failed).
- Backend pagination params (`limit`/`offset`) exist but are not required for v1 — a
  single unpaginated fetch on load is fine; wire up "load more" only if there's time.

**`GET /reports/report/{report_id}`** — requires auth. Returns ONE of two possible
shapes, distinguished by the presence of a `content` key:

Shape A — still in progress (no `content` key):

```json
{ "report_id": "string (uuid)", "status": "string" }
```

Shape B — completed (has a `content` key, though several fields may be `null`):

```json
{
  "report_id": "string (uuid)",
  "goal": "string",
  "intent": "string | null",
  "categories": ["string"] | null,
  "strategy_summary": "string | null",
  "title": "string | null",
  "content": "string | null",
  "created_at": "string (ISO datetime)",
  "updated_at": "string (ISO datetime)"
}
```

Logic for the report page, on initial load:

1. Fetch this endpoint.
2. If the response has no `content` key (Shape A): show the in-progress UI (stepper +
   status log) using `status` to seed the initial stepper state, then open the
   WebSocket (below) to receive live updates.
3. If the response has a `content` key (Shape B) and `content` is non-null: render the
   completed report UI directly — no WebSocket needed.
4. If Shape B is returned but `content` is `null` (edge case — treat as still
   in-progress): fall back to the in-progress UI and open the WebSocket anyway.

`content` is a **Markdown string** — render it with a Markdown renderer (e.g.
`react-markdown`), styled per the "long-form reading" typography rules in `DESIGN.md`
(Source Serif 4 for body/headings within the report, generous line-height, constrained
reading-width column). Do not render it as raw text or raw HTML.

### Live updates — WebSocket

**`ws://localhost:8000/ws/{report_id}?token={access_token}`**

Connect only while a report is in progress (Shape A, or Shape B with null `content`),
per the logic above. Pass the JWT as the `token` query parameter — there is no
`Authorization` header mechanism for WebSocket connections.

Each message received is JSON:

```json
{ "phase": "string", "status": "string", "done": boolean }
```

Observed `phase` values: `planning`, `research`, `synthesis`, `done`, `failed`.
Observed `status` values per phase include `starting`, `finished`, and for the research
phase specifically, per-task updates shaped like `task_{task_id}_{status}` (e.g.
`task_task_1_running`, `task_task_1_done`) — these can be surfaced in the status log
as-is, or parsed further for a per-task view if time allows, but are not required to
be parsed for v1.

Behavior:

- Use incoming messages to advance the stepper UI (Planning -> Researching ->
  Synthesizing) and append entries to the quiet status log, matching the visual
  treatment in `research_report_in_progress`.
- When a message arrives with `done: true` (this can happen on the `done` phase for
  success, or the `failed` phase for failure), close the WebSocket and re-fetch
  `GET /reports/report/{report_id}`:
  - If the re-fetch now returns Shape B with non-null `content`, switch to the
    completed report UI.
  - If the phase that triggered `done: true` was `failed`, show the failed-state UI
    instead (quiet terracotta/error message, original query still visible, no stepper).
- Handle WebSocket connection errors gracefully — if the socket fails to connect or
  drops unexpectedly before a `done` message, show a non-blocking inline notice and
  allow the user to manually refresh, rather than leaving the page silently stuck.

## State & auth handling

- A minimal auth context/hook (`useAuth`) that exposes the current token, a `login`
  function (stores token, likely via the signup/signin response), and a `logout`
  function (clears `localStorage`, redirects to `/login`).
- A route guard component/wrapper for protected routes that checks for a token and
  redirects to `/login` if absent — apply it to `/chat` and `/report/:reportId`.
- No need for global state management (Redux/Zustand/etc.) — React context plus local
  component state is sufficient for this app's scope.

## Explicitly out of scope for this pass

Do not build: settings page, user profile page, report deletion, report editing,
pagination UI beyond a simple initial list fetch, or any page/route not listed
above.

Note: light mode is no longer out of scope — the redesign shipped both `paper`
and `ink` themes behind a toggle (see "Design system").
