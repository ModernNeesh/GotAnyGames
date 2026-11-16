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
      groups.py          # Groups, membership, and per-group preferences
      recs.py            # GET /get_recs/{group_id} - group recommendations
    group_preferences.py # Shared group preference aggregation
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
        Home.tsx               # Dashboard with "My Games" and "Groups"
        MyGames.tsx            # Search, rate, and manage personal game list
        Groups.tsx             # List and create groups
        GroupDetail.tsx        # Members, per-member preferences, and group summary
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

## Groups and Preferences

### Access and API behavior

- Group routes use `get_current_user` for Supabase UUID identity. Membership
  checks use `require_group_member`; missing groups and nonmembers receive the
  same `404` with `{"detail":"Group not found"}`.
- Any current member can rename the group, search for and add existing users,
  remove another member (including the creator), and view members' preferences.
  Members can update only their own preferences and leave only as themselves.
  There is no owner/admin role or invitation/acceptance workflow. Authenticated,
  synced users can still self-join by group ID through `POST /join_group/`.
- Group creation and rename trim names and require 1-100 characters. Creation
  requires a synced app user and automatically adds the creator as a member.
  Group request schemas reject extra fields, including attempts to supply the
  acting user's identity where it must come from authentication.

| Method and path | Contract |
| --- | --- |
| `GET /my_groups/` | Only the caller's groups, ordered by name then ID; no memberships returns `[]`. A `user_id` query parameter cannot select another user's groups. |
| `POST /create_group/` | Body `{name}`; returns `{id, name}`. Missing creator returns `404`. |
| `PATCH /rename_group/` | Body `{id, name}`; requires membership and returns `{id, name}`. |
| `GET /groups/{group_id}` | Returns `{id, name, members}`; members ordered by case-insensitive name then UUID. |
| `GET /group_platforms/` | Authenticated platform catalog `{id, name}[]`, ordered by case-insensitive name then ID; no group membership required. |
| `GET /groups/{group_id}/users?query=...` | Display-name substring search excluding current members. Query length 2-100; trim whitespace and require at least two remaining characters. Escape SQL wildcards; return at most 20 matches ordered by case-insensitive name then UUID. |
| `POST /groups/{group_id}/members` | Body `{user_id: UUID}`; immediately adds an existing user and returns updated group detail. Missing user returns `404`; duplicate membership or integrity conflict returns `409`. |
| `DELETE /groups/{group_id}/members/{member_id}` | Removes target membership and this group's preferences atomically; returns updated detail. Missing target returns `404`; self-removal returns `400` (use leave); invalid UUID returns `422`. |
| `POST /join_group/` | Body `{group_id}`; self-join returns `{user, group}`. No invitations, approval, or add-member route's duplicate/conflict handling. |
| `DELETE /leave_group/` | Body `{group_id}`; removes only caller's membership and preferences for this group atomically; returns `{user, group}`. Empty groups remain. |
| `GET /groups/{group_id}/members/{member_id}/preferences` | Caller and target must both belong to group; returns target's preferences or `{platforms: []}`. |
| `PATCH /groups/{group_id}/preferences` | Replaces caller's complete preference selection; returns saved preferences ordered by platform ID. |
| `GET /groups/{group_id}/preferences/summary` | Returns current members' aggregate preferences as described below. |

Successful group responses use `200`, including creation and member addition.
Request validation uses `422`; authentication failures use the existing auth
dependency's `401`/`403` behavior.

### Preference validation and storage

- Request/response shape: `{"platforms":[{"platform_id":1,"online":true,"offline":false}]}`.
  Modes belong to each platform independently; the former flat
  `{platform_ids, online, offline}` shape is obsolete.
- Updates require a nonempty list, unique positive strict integer platform IDs,
  actual JSON booleans, and at least one mode per platform. Both modes may be
  true. Extra fields are rejected on requests and nested entries. Verify every
  platform exists before replacing saved values; invalid updates preserve them.
  `{platforms: []}` is only a read default, not a valid update.
- `GroupUserPreference` maps to `group_user_preferences` with composite primary
  key `(group_id, user_id, platform_id)`, foreign keys to `groups`, `users`, and
  `platforms_lookup`, and required `online`/`offline` boolean columns. User IDs
  remain UUIDs. Save replaces only the current `(group_id, user_id)` rows.
  Group preferences neither inherit nor overwrite global `user_prefs`.
- Removal/leave cleanup preserves user accounts, other members' preferences,
  global preferences, and data in other groups.
- Saves, removals, and leaving call `require_group_member(..., lock=True)`.
  A separate `SELECT ... FOR UPDATE` locks the group row before membership checks
  to serialize these operations on PostgreSQL and prevent saves from recreating
  departed members' preferences. Preserve this transaction boundary.
- Router helpers `group_detail` and `group_preferences` handle consistent member
  and platform ordering. Schemas live in `app/models/schemas.py`.
- Per-platform modes and member removal require no schema change. Database
  initialization uses SQLAlchemy `create_all()` to create missing registered
  tables; it does not alter existing columns or constraints.

### Preference summaries and frontend

- `app.group_preferences.summarize_group_preferences(session, group_id)` returns
  `GroupPreferenceSummaryModel` in one SQL statement using the caller's session;
  authorization is the caller's responsibility. No stored aggregates are used.
- The result includes group `member_count` and the union of platforms selected
  by current members, ordered by descending platform member count, then
  case-insensitive platform name and ID. Each platform includes ID/name, member
  count/percentage, and online/offline counts/percentages.
- Platform percentage divides by all current members, including those without
  preferences. Mode percentages divide by members selecting that platform.
  Both modes count independently, so percentages may sum above 100%. Keep raw
  counts and unrounded percentages on a 0-100 scale for recommendations; the UI
  displays at most one decimal place.
- Exclude global preferences, other groups, and stale rows for departed members.
  No saved preferences returns `platforms: []`; the helper returns member count
  zero for an empty group.
- Group detail has Members and Group preferences tabs, with arrow/Home/End
  navigation. Summary loads when its tab opens and refreshes after preference
  saves; returning to the tab reflects membership changes. Preserve loading,
  empty, and retry states.

### Current recommendations

- `GET /get_recs/{group_id}` requires authentication and membership with the same
  `404` behavior as group routes. It returns `{group_id, games, ratings}`.
- `app/routers/recs.py` selects games rated by every current member, ordered by
  descending group average rating then game ID. Its helper defaults to one game
  and accepts `num_games` to limit results.
- Candidates must support at least two players on one of the three most popular
  group platforms in that platform's preferred mode. Platform ties prefer
  stronger mode agreement then platform ID; online wins a mode tie.
- Full game data can expand a game into distinct multiplayer feature rows.
  Repeat its fractional average rating for each returned row so `games` and
  `ratings` stay aligned. No matches returns empty lists.
- The GroupDetail recommendation action is still a coming-soon placeholder.

## Backend Verification

Run from `backend/` with its Python environment:

```sh
python -m unittest discover -s tests -v
```

- `tests/test_groups.py` covers membership/auth boundaries, ordering, validation,
  wildcard search, member additions/removals, preference replacement/isolation,
  leave cleanup (including the last member), rollback on failed removal commits,
  and summary counts, denominators, sorting, and recalculation.
- `tests/test_recs.py` covers recommendation selection, ties, fractional rating
  serialization, route registration, and access control.
- Tests use isolated in-memory SQLite, stub `app.database` to avoid production
  initialization, replace session factories, and override authentication. The
  recommendation tests also stub the PostgreSQL-specific full-game loader.
  They do not verify live Supabase JWTs, production PostgreSQL, or PostgreSQL
  row-lock/concurrent save-removal behavior.

## Future Plans

- Connect the group detail recommendation action to the existing backend route.
- Expand the initial recommendation algorithm beyond games every member has
  already rated, using members' ratings, platforms, and preferences.
