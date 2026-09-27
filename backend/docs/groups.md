# Group API and preferences

The group detail page uses `app/routers/groups.py` to load members, add existing
users, and read or save preferences for one group. User identity comes from the
Supabase JWT through `get_current_user`; authenticated requests send
`Authorization: Bearer <access_token>`.

## Access rules

- A current member can view a group, search for users to add, add an existing
  user, rename the group, and view fellow members' group preferences.
- A member can update only their own preferences and leave only as themselves.
  The preference update payload does not accept a user ID.
- Membership-protected routes return `404` with `{"detail":"Group not found"}`
  for both a missing group and a caller who is not a member.
- There is no owner/admin role or invitation/acceptance workflow. The existing
  `POST /join_group/` route still lets an authenticated, synced user join an
  existing group by its ID. These groups are therefore not invitation-private.

## New endpoints

All successful responses below use status `200`, including member creation.

| Method and path | Input | Behavior and response |
| --- | --- | --- |
| `GET /groups/{group_id}` | Integer group ID | Returns the group's `id`, `name`, and `members`. Members are ordered by case-insensitive name, then UUID. |
| `GET /group_platforms/` | None | Returns all platform catalog entries as `{id, name}`, ordered by case-insensitive name, then ID. Requires authentication but no particular group membership. |
| `GET /groups/{group_id}/users?query=...` | Required search text, 2–100 characters | Searches existing app users by case-insensitive display-name substring, excluding current members. Trims surrounding whitespace and requires at least two remaining characters. Escapes SQL wildcard characters, returns at most 20 matches, and orders by case-insensitive name, then UUID. |
| `POST /groups/{group_id}/members` | `{"user_id":"<UUID>"}` | Adds an existing app user immediately and returns the updated group detail. Returns `404` if the target user does not exist, or `409` for an existing membership or an integrity conflict during the add. |
| `GET /groups/{group_id}/members/{member_id}/preferences` | Group ID and member UUID | Requires both the caller and target user to belong to the group. Returns the target member's preferences, or empty defaults if they have not saved any. |
| `PATCH /groups/{group_id}/preferences` | `platform_ids`, `online`, `offline` | Replaces the caller's complete preference selection for this group and returns the saved values. Platform IDs are returned in ascending order. |

For example, `GET /groups/20` can return:

```json
{
  "id": 20,
  "name": "Game night",
  "members": [
    {"id": "00000000-0000-0000-0000-000000000001", "name": "Alex"},
    {"id": "00000000-0000-0000-0000-000000000002", "name": "Sam"}
  ]
}
```

To save preferences, send a complete body to `PATCH /groups/20/preferences`:

```json
{
  "platform_ids": [1, 2],
  "online": true,
  "offline": false
}
```

Here, `1` and `2` must be IDs returned by the platform catalog. This selects
online play for both platforms; online/offline choices are shared across every
selected platform. The response has the same shape. A member without saved
preferences receives:

```json
{"platform_ids": [], "online": false, "offline": false}
```

That empty value is a read default, not a valid update. Updates require at least
one platform and one play mode.

## Existing routes used or updated

| Method and path | Behavior |
| --- | --- |
| `GET /my_groups/` | Existing listing route used by the Groups page. Returns only the authenticated user's groups as `{id, name}`, ordered by group name and then ID. A user without memberships receives `[]`; a `user_id` query parameter cannot select another user's groups. |
| `POST /create_group/` | Pre-existing creation route now used by the Create group form. Accepts `{"name":"Game night"}`, creates the group, and adds its creator as the first member. Returns `{id, name}`. Name validation now trims whitespace and enforces 1–100 characters. A creator missing from the app's users table receives `404`; login's `/auth/sync` normally creates that user row. |
| `DELETE /leave_group/` | Accepts `{"group_id":20}`. Now checks membership and deletes only the departing user's preferences for that group before removing their membership, in the same transaction. Returns `{user, group}`. Other members, other groups, and global preferences are unaffected. An empty group remains after its last member leaves. |
| `PATCH /rename_group/` | Accepts `{"id":20,"name":"Friday games"}`. Now requires authentication and membership; previously this route lacked those checks. Uses the same trimmed 1–100-character name validation as creation and returns `{id, name}`. |
| `POST /join_group/` | Pre-existing self-join route, unchanged by the detail-page work. Accepts `{"group_id":20}` and adds the authenticated user to an existing group. Returns `{user, group}`. It does not implement invitations, owner approval, or the new add-member route's duplicate/conflict handling. |

## Schemas and validation

`app/models/schemas.py` adds `GroupDetailModel`, `GroupPlatformModel`, and
`GroupPreferencesModel` for responses, plus `AddGroupMemberRequest` and
`GroupPreferencesRequest` for requests. `RenameGroupRequest` now inherits the
creation name rules from `CreateGroupRequest`.

Preference updates require a nonempty list of unique, positive integer platform
IDs and actual JSON booleans for `online` and `offline`; numeric strings and
booleans are not accepted as platform IDs. At least one mode must be `true`.
The route also verifies that every selected platform exists before deleting any
saved values. Invalid selections therefore leave the previous preferences intact.
Extra fields are forbidden on these request schemas, including attempts to set
the acting user's identity in creation or preference requests.

Validation errors use `422`. Missing authentication is rejected by the existing
auth dependency (`401`/`403`, depending on the authentication failure and library
behavior). Membership/target lookup failures use `404`; the new add-member route
uses `409` for duplicate or conflicting membership changes.

## Storage and helpers

`app/models/db.py` adds `GroupUserPreference`, mapped to
`group_user_preferences`. Its composite primary key is
`(group_id, user_id, platform_id)`, with foreign keys to `groups`, `users`, and
`platforms_lookup`. User IDs remain Supabase UUIDs. `online` and `offline` are
required boolean columns, not part of the key.

Each selected platform gets one row. Saving replaces only rows belonging to the
current `(group_id, user_id)` pair, copying the same online/offline flags to each
platform. This table is separate from `user_prefs`; group settings neither inherit
nor overwrite a user's global preferences.

Three router helpers centralize the behavior:

- `require_group_member` fetches a group through its membership and provides the
  shared `404` behavior. Preference reads call it for both caller and target.
- `group_detail` serializes the group and consistently orders its members.
- `group_preferences` loads one member's rows for one group, sorts platform IDs,
  and aggregates each mode with `any()`. No rows produce the empty defaults.

The existing database initialization calls SQLAlchemy `create_all()` when a
registered table is missing. On backend startup, it can create this new table
using the configured database connection. This is not a schema migration:
`create_all()` does not alter columns or constraints on tables that already exist.

## Verification and scope

`tests/test_groups.py` contains 22 tests: five for group listing and 17 for the
detail workflow. They cover authentication and membership boundaries, ordering,
creation validation, search limits and escaped wildcards, additions, preference
validation and isolation, and leave-group cleanup, including the last member.

The suite uses an isolated in-memory SQLite database, replaces the router's
session factory, and overrides authentication for authenticated cases. It imports
the router with a stub `app.database` module to avoid initializing the production
database. These tests do not verify live Supabase JWTs or production PostgreSQL
deployment. Run from `backend/` with its Python environment:

```sh
python -m unittest discover -s tests -p test_groups.py
```

No recommendation endpoint or recommendation engine was added. The detail page's
recommendation action remains a coming-soon placeholder.
