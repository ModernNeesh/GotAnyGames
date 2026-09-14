# GotAnyGames

This file gives Codex and other coding agents the repo-specific context needed to
work safely in GotAnyGames.

GotAnyGames is a video game recommendation platform for groups of friends. Users
build personal game libraries with ratings, then form groups to get multiplayer
game recommendations based on shared preferences, platforms, and play styles.

## Stack

- Backend: Python 3, FastAPI, SQLAlchemy ORM, Supabase PostgreSQL
- Frontend: React 19, TypeScript, Vite 6, component-specific plain CSS
- Auth: Supabase Auth (email/password + Google OAuth), ES256 JWT verification via JWKS
- Infrastructure: Docker Compose (backend :8000, frontend :5173)
- Data pipeline: IGDB API ingestion (`backend/pipeline/`) - extracts, transforms, and loads game data

## Project Structure

```text
backend/
  app/
    main.py              # FastAPI app, CORS, router registration
    auth.py              # JWT verification (ES256/JWKS) -> get_current_user dependency
    database.py          # Engine/session init from POSTGRES_URL
    models/
      db.py              # SQLAlchemy models (Game, User, UserRating, Group, etc.)
      schemas.py         # Pydantic request/response models
    routers/
      auth.py            # POST /auth/sync - upsert user after Supabase login
      games.py           # GET /search_game/{query}, GET /full_game_data/{game_id}
      ratings.py         # POST /rate_game/, GET /my_ratings/, DELETE /delete_rating/{game_id}
      users.py           # PATCH /rename_user/, POST /add_user_prefs/
      groups.py          # CRUD for groups and membership
  pipeline/              # IGDB data ingestion scripts (extract -> transform -> load)

frontend/
  src/
    contexts/AuthContext.tsx   # Supabase auth state, signIn/signUp/signOut, /auth/sync call
    components/
      tsx/
        ProtectedRoute.tsx     # Redirects to /login if unauthenticated
        GameSearch.tsx         # Debounced search input with dropdown results
        GameList.tsx           # Rated games list with edit/delete actions
      css/                     # Component-specific stylesheets
    pages/
      tsx/
        Login.tsx              # Email/password + Google OAuth login
        Home.tsx               # Dashboard with "My Games" and "Groups" (coming soon)
        MyGames.tsx            # Search, rate, and manage personal game list
      css/                     # Page-specific stylesheets
    lib/
      supabase.ts              # Supabase client init
      api.ts                   # Fetch wrapper with auto-attached JWT
    types.ts                   # Shared TypeScript interfaces
```

## Running Locally

```bash
# Requires .env with:
# CLIENT_ID, CLIENT_SECRET, POSTGRES_URL, SUPABASE_URL, SUPABASE_ANON_KEY
docker compose up --build
```

Backend: http://localhost:8000 (Swagger UI at /docs)
Frontend: http://localhost:5173

If dependencies change, clear Docker's anonymous volume first:

```bash
docker compose down -v
docker compose up --build
```

## Key Architecture Decisions

- User IDs are Supabase Auth UUIDs, not auto-increment integers. The `users.id`
  column is `UUID` type. All user-related foreign keys (`user_ratings`,
  `user_prefs`, `group_membership`) reference UUIDs.
- Auth flow: frontend authenticates via Supabase JS SDK, sends the JWT in the
  `Authorization: Bearer` header, backend verifies with ES256 via the Supabase
  JWKS endpoint, then extracts the user UUID from the `sub` claim.
- `/auth/sync` is called after every login to upsert the user row in the app
  database.
- Game search uses the `slug` column with `ILIKE` matching. Results prioritize
  `game_type == 0` (main games) over DLC/expansions.

## Gotchas

- `.gitignore` blocks `frontend/src/lib/`: The `lib/` pattern for Python
  packaging matches `frontend/src/lib/`. Use `git add -f` to force-add files in
  that directory.
- Docker node_modules caching: The anonymous volume `- /frontend/node_modules`
  in `docker-compose.yml` persists node_modules across builds. After adding new
  npm dependencies, run `docker compose down -v` to clear it.
- Frontend styling uses plain CSS files imported by their corresponding React
  components. Global color variables and browser reset styles live in
  `frontend/src/App.css`.

## Agent Guidance

- Follow the existing FastAPI router, SQLAlchemy model, Pydantic schema, React,
  and TypeScript patterns before introducing new abstractions.
- Keep backend user identity aligned with Supabase Auth UUIDs throughout models,
  schemas, route parameters, and frontend API calls.
- Preserve the frontend auth flow: Supabase session state in
  `AuthContext.tsx`, protected routes through `ProtectedRoute.tsx`, and backend
  calls through `frontend/src/lib/api.ts`.
- When changing dependencies, account for Docker's cached anonymous
  `node_modules` volume during verification.

## Future Plans

- Groups feature: Users create groups, invite friends, and get multiplayer game
  recommendations based on overlapping libraries, platforms, and preferences.
  Backend endpoints exist (`groups.py`) but the frontend page is not yet built.
- Game recommendation engine: Analyze group members' ratings, platforms, and
  preferences to suggest games everyone can play together.
