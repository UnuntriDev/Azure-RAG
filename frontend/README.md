# Frontend — Azure RAG Assistant

Next.js 15 (App Router) · TypeScript · Tailwind v4 · shadcn/ui · React Query.
UI for the [Azure RAG Knowledge Assistant](../README.md) — upload documents, chat with
streaming answers grounded in your files (with citations), browse history and agent traces.

## Run

```bash
npm install
npm run dev            # http://localhost:3000
```

Point it at the backend with `NEXT_PUBLIC_API_URL` (defaults to `http://localhost:8000`):

```bash
# frontend/.env.local
NEXT_PUBLIC_API_URL=http://localhost:8000
# Optional — enables Google login. Must match the backend's GOOGLE_CLIENT_ID.
NEXT_PUBLIC_GOOGLE_CLIENT_ID=
# Optional — show the Traces tab (debug / admin).
NEXT_PUBLIC_SHOW_TRACES=false
```

When `NEXT_PUBLIC_GOOGLE_CLIENT_ID` is unset the app runs unauthenticated (local dev).
When set, login goes through Google and the session lives in an HttpOnly cookie set by the
backend — JS never touches the raw token. All API calls use `credentials: "include"`.

## Pages

| Route | Purpose |
|-------|---------|
| `/`          | Chat — streaming answers, file-scoped context, RAG or agent mode |
| `/documents` | Upload + manage documents (status, analyze, delete) |
| `/historia`  | Conversation history |
| `/slady`     | Agent/RAG traces (gated by `NEXT_PUBLIC_SHOW_TRACES`) |
| `/settings`  | Prompt version + preferences |

## Structure

- `app/` — App Router pages + `providers.tsx` (React Query + auth context)
- `components/` — feature components; `components/ui/` are shadcn primitives
- `lib/api.ts` — typed fetch wrapper (single source of truth for backend calls)
- `lib/auth.ts` — Google login / logout / session restore
- `types/api.ts` — TypeScript mirrors of the backend Pydantic schemas

See [`AGENTS.md`](AGENTS.md) for the conventions this codebase follows.

## Quality

```bash
npm run lint           # eslint
npx tsc --noEmit       # type-check
npm run build          # production build
```
