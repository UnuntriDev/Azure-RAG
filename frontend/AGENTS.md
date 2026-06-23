# Frontend — Azure RAG Assistant

Next.js 15 (App Router) + TypeScript + Tailwind v4 + shadcn/ui. Talks to the FastAPI
backend at `http://localhost:8000` (override with `NEXT_PUBLIC_API_URL`). See `lib/api.ts`.

## Conventions

- Server Components by default; `"use client"` only for forms, hooks, and interactivity.
- API shapes live in `types/api.ts` (mirror the backend Pydantic schemas) — single source of
  truth, imported by `lib/api.ts`. No `any`.
- Data fetching via React Query (`@tanstack/react-query`); forms via `react-hook-form` + `zod`.
- Use shadcn/ui primitives from `components/ui/`; compose Tailwind with `cn()` from `lib/utils.ts`.
- Every list/fetch has loading + empty + error states (use `Skeleton`).
