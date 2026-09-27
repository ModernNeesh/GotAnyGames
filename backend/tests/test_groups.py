"""Isolated API coverage for group lists, detail-page actions, and preferences.

Requests run directly through a test FastAPI app and an in-memory SQLite DB.
The production database module is replaced before importing the router, and
get_current_user is overridden to exercise different callers without real
tokens. Clearing the override checks rejection of unauthenticated requests;
these tests do not exercise live Supabase JWT verification or PostgreSQL.

Run from backend: ../.venv/Scripts/python.exe -m unittest discover -s tests -v
"""

import asyncio
import json
import sys
import unittest
from types import ModuleType
from unittest.mock import patch
from uuid import UUID

from fastapi import FastAPI
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth import get_current_user
from app.models.db import Base, Group, GroupUserPreference, Platform, User, UserPref, group_membership


@compiles(PgUUID, "sqlite")
def sqlite_uuid_type(_type, _compiler, **_kwargs):
    # SQLite's UUID type has numeric affinity, which corrupts all-digit test UUIDs.
    return "CHAR(32)"


# Import the router without initializing or connecting to the production database.
test_database = ModuleType("app.database")
test_database.Session = None
with patch.dict(sys.modules, {"app.database": test_database}):
    from app.routers import groups


async def get_response(app, query_string=b"", *, path="/my_groups/", method="GET", payload=None):
    """Send one ASGI request and return (status, decoded JSON) without a server."""
    messages = []
    request_body = json.dumps(payload).encode() if payload is not None else b""

    async def receive():
        return {"type": "http.request", "body": request_body, "more_body": False}

    async def send(message):
        messages.append(message)

    await app(
        {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": method,
            "scheme": "http",
            "path": path,
            "raw_path": path.encode(),
            "query_string": query_string,
            "root_path": "",
            "headers": [(b"content-type", b"application/json")] if payload is not None else [],
            "client": ("127.0.0.1", 12345),
            "server": ("test", 80),
        },
        receive,
        send,
    )
    status = next(message["status"] for message in messages if message["type"] == "http.response.start")
    body = b"".join(message.get("body", b"") for message in messages if message["type"] == "http.response.body")
    return status, json.loads(body)


class MyGroupsTests(unittest.TestCase):
    """Verify authenticated group-list filtering, ordering, and empty states."""

    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(
            self.engine,
            tables=[User.__table__, Group.__table__, group_membership],
        )
        self.session_factory = sessionmaker(bind=self.engine)
        self.addCleanup(self.engine.dispose)
        self.session_patch = patch.object(groups, "Session", self.session_factory)
        self.session_patch.start()
        self.addCleanup(self.session_patch.stop)

        self.user_id = UUID("00000000-0000-0000-0000-000000000001")
        self.other_user_id = UUID("00000000-0000-0000-0000-000000000002")
        with self.session_factory() as session:
            member = User(id=self.user_id, name="Member")
            other = User(id=self.other_user_id, name="Other")
            session.add_all([
                Group(id=30, name="Weekend", users=[member]),
                Group(id=20, name="Friends", users=[member, other]),
                Group(id=10, name="Friends", users=[member]),
                Group(id=40, name="Private", users=[other]),
            ])
            session.commit()

        self.app = FastAPI()
        self.app.include_router(groups.router)
        self.app.dependency_overrides[get_current_user] = lambda: self.user_id

    def test_returns_only_memberships_in_stable_name_and_id_order(self):
        status, body = asyncio.run(get_response(self.app))
        self.assertEqual(status, 200)
        self.assertEqual(body, [
            {"id": 10, "name": "Friends"},
            {"id": 20, "name": "Friends"},
            {"id": 30, "name": "Weekend"},
        ])

    def test_query_parameter_cannot_select_another_users_groups(self):
        status, body = asyncio.run(
            get_response(self.app, f"user_id={self.other_user_id}".encode())
        )
        self.assertEqual(status, 200)
        self.assertEqual([group["id"] for group in body], [10, 20, 30])

    def test_user_without_memberships_receives_empty_list(self):
        with self.session_factory() as session:
            session.execute(
                group_membership.delete().where(group_membership.c.user_id == self.user_id)
            )
            session.commit()
        self.assertEqual(asyncio.run(get_response(self.app)), (200, []))

    def test_user_not_yet_synced_receives_empty_list(self):
        self.app.dependency_overrides[get_current_user] = lambda: UUID(int=3)
        self.assertEqual(asyncio.run(get_response(self.app)), (200, []))

    def test_missing_authentication_is_rejected(self):
        self.app.dependency_overrides.clear()
        status, _ = asyncio.run(get_response(self.app))
        self.assertIn(status, (401, 403))


class GroupDetailTests(unittest.TestCase):
    """Verify membership rules, input validation, and scoped preference writes.

    Reuse the group-list fixture and add platforms plus an eligible new member.
    These tests also check that rejected saves preserve old preferences and
    that leaving affects only the caller's membership and settings in one group.
    """

    def setUp(self):
        MyGroupsTests.setUp(self)
        Base.metadata.create_all(
            self.engine,
            tables=[Platform.__table__, GroupUserPreference.__table__, UserPref.__table__],
        )
        self.third_user_id = UUID(int=3)
        with self.session_factory() as session:
            session.add_all([
                Platform(id=1, name="PC"),
                Platform(id=2, name="Nintendo Switch"),
                User(id=self.third_user_id, name="Third Friend"),
            ])
            session.commit()

    def request(self, path, method="GET", payload=None, query_string=b""):
        return asyncio.run(get_response(
            self.app, query_string, path=path, method=method, payload=payload,
        ))

    def test_group_detail_has_members_in_stable_name_order(self):
        self.assertEqual(self.request("/groups/20"), (200, {
            "id": 20,
            "name": "Friends",
            "members": [
                {"id": str(self.user_id), "name": "Member"},
                {"id": str(self.other_user_id), "name": "Other"},
            ],
        }))

    def test_missing_and_nonmember_groups_have_identical_responses(self):
        self.assertEqual(self.request("/groups/40"), self.request("/groups/999"))
        self.assertEqual(self.request("/groups/40")[0], 404)

    def test_create_trims_name_and_adds_creator(self):
        status, body = self.request("/create_group/", "POST", {"name": "  Game night  "})
        self.assertEqual(status, 200)
        self.assertEqual(body["name"], "Game night")
        detail = self.request(f"/groups/{body['id']}")[1]
        self.assertEqual(detail["members"], [{"id": str(self.user_id), "name": "Member"}])

    def test_create_rejects_empty_long_and_forged_identity(self):
        for payload in [
            {"name": "   "}, {"name": ""}, {"name": "x" * 101},
            {"name": "Friends", "user_id": str(self.other_user_id)},
        ]:
            with self.subTest(payload=payload):
                self.assertEqual(self.request("/create_group/", "POST", payload)[0], 422)

    def test_unsynced_creator_is_rejected_without_creating_group(self):
        self.app.dependency_overrides[get_current_user] = lambda: UUID(int=999)
        self.assertEqual(self.request("/create_group/", "POST", {"name": "New"})[0], 404)
        with self.session_factory() as session:
            self.assertEqual(session.query(Group).count(), 4)

    def test_user_search_matches_display_name_and_excludes_members(self):
        status, users = self.request("/groups/20/users", query_string=b"query=tH")
        self.assertEqual(status, 200)
        self.assertEqual(users, [{"id": str(self.third_user_id), "name": "Third Friend"}])

    def test_search_bounds_and_wildcards(self):
        for query in [b"query=a", b"query=++", b"query=" + b"x" * 101]:
            with self.subTest(query=query):
                self.assertEqual(self.request("/groups/20/users", query_string=query)[0], 422)
        self.assertEqual(self.request("/groups/20/users", query_string=b"query=%25%25"), (200, []))
        with self.session_factory() as session:
            session.add_all([User(id=UUID(int=i + 100), name=f"Player {i:02}") for i in range(25)])
            session.commit()
        status, users = self.request("/groups/20/users", query_string=b"query=Player")
        self.assertEqual(status, 200)
        self.assertEqual(len(users), 20)
        self.assertEqual(users[0]["name"], "Player 00")

    def test_add_existing_user_returns_updated_detail_and_rejects_duplicates(self):
        payload = {"user_id": str(self.third_user_id)}
        status, body = self.request("/groups/20/members", "POST", payload)
        self.assertEqual(status, 200)
        self.assertEqual([member["id"] for member in body["members"]], [
            str(self.user_id), str(self.other_user_id), str(self.third_user_id),
        ])
        self.assertEqual(self.request("/groups/20/members", "POST", payload)[0], 409)
        self.assertEqual(self.request("/groups/20/members", "POST", {"user_id": str(UUID(int=999))})[0], 404)

    def test_platform_catalog_is_authenticated_and_sorted(self):
        self.assertEqual(self.request("/group_platforms/"), (200, [
            {"id": 2, "name": "Nintendo Switch"}, {"id": 1, "name": "PC"},
        ]))

    def test_default_preferences_are_empty_and_only_members_are_visible(self):
        self.assertEqual(self.request(f"/groups/20/members/{self.other_user_id}/preferences"), (200, {
            "platform_ids": [], "online": False, "offline": False,
        }))
        self.assertEqual(self.request(f"/groups/20/members/{self.third_user_id}/preferences")[0], 404)

    def test_preferences_replace_only_caller_and_group_without_changing_global_preferences(self):
        with self.session_factory() as session:
            session.add_all([
                GroupUserPreference(group_id=20, user_id=self.user_id, platform_id=1, online=True, offline=False),
                GroupUserPreference(group_id=10, user_id=self.user_id, platform_id=1, online=True, offline=False),
                GroupUserPreference(group_id=20, user_id=self.other_user_id, platform_id=1, online=True, offline=False),
                UserPref(user_id=self.user_id, platform_id=1, online=True, offline=False),
            ])
            session.commit()
        payload = {"platform_ids": [2], "online": False, "offline": True}
        self.assertEqual(self.request("/groups/20/preferences", "PATCH", payload), (200, payload))
        self.assertEqual(self.request(f"/groups/20/members/{self.user_id}/preferences"), (200, payload))
        original = {"platform_ids": [1], "online": True, "offline": False}
        self.assertEqual(self.request(f"/groups/10/members/{self.user_id}/preferences"), (200, original))
        self.assertEqual(self.request(f"/groups/20/members/{self.other_user_id}/preferences"), (200, original))
        with self.session_factory() as session:
            prefs = session.query(UserPref).filter_by(user_id=self.user_id).all()
            self.assertEqual([(row.platform_id, row.online, row.offline) for row in prefs], [(1, True, False)])

    def test_preferences_validate_platforms_and_modes_without_erasing_saved_values(self):
        original = {"platform_ids": [1], "online": True, "offline": False}
        self.assertEqual(self.request("/groups/20/preferences", "PATCH", original)[0], 200)
        for payload in [
            {**original, "platform_ids": []},
            {**original, "platform_ids": [1, 1]},
            {**original, "platform_ids": [0]},
            {**original, "platform_ids": [-1]},
            {**original, "platform_ids": [999]},
            {**original, "platform_ids": [True]},
            {**original, "online": False},
            {**original, "online": "yes"},
            {**original, "user_id": str(self.other_user_id)},
        ]:
            with self.subTest(payload=payload):
                self.assertEqual(self.request("/groups/20/preferences", "PATCH", payload)[0], 422)
        self.assertEqual(self.request(f"/groups/20/members/{self.user_id}/preferences"), (200, original))

    def test_multi_platform_preferences_are_saved_with_shared_modes_in_id_order(self):
        payload = {"platform_ids": [2, 1], "online": True, "offline": True}
        self.assertEqual(self.request("/groups/20/preferences", "PATCH", payload), (200, {
            **payload, "platform_ids": [1, 2],
        }))

    def test_nonmembers_cannot_read_search_add_edit_or_leave_group(self):
        for path, method, payload, query in [
            ("/groups/40", "GET", None, b""),
            ("/groups/40/users", "GET", None, b"query=Third"),
            ("/groups/40/members", "POST", {"user_id": str(self.user_id)}, b""),
            (f"/groups/40/members/{self.other_user_id}/preferences", "GET", None, b""),
            ("/groups/40/preferences", "PATCH", {"platform_ids": [1], "online": True, "offline": False}, b""),
            ("/leave_group/", "DELETE", {"group_id": 40}, b""),
            ("/rename_group/", "PATCH", {"id": 40, "name": "Changed"}, b""),
        ]:
            with self.subTest(path=path):
                self.assertEqual(self.request(path, method, payload, query)[0], 404)

    def test_all_group_routes_require_authentication(self):
        self.app.dependency_overrides.clear()
        for path, method, payload, query in [
            ("/groups/20", "GET", None, b""),
            ("/group_platforms/", "GET", None, b""),
            ("/groups/20/users", "GET", None, b"query=Third"),
            ("/groups/20/members", "POST", {"user_id": str(self.third_user_id)}, b""),
            (f"/groups/20/members/{self.user_id}/preferences", "GET", None, b""),
            ("/groups/20/preferences", "PATCH", {"platform_ids": [1], "online": True, "offline": False}, b""),
            ("/create_group/", "POST", {"name": "New"}, b""),
            ("/leave_group/", "DELETE", {"group_id": 20}, b""),
            ("/rename_group/", "PATCH", {"id": 20, "name": "Changed"}, b""),
        ]:
            with self.subTest(path=path):
                self.assertIn(self.request(path, method, payload, query)[0], (401, 403))

    def test_leave_removes_only_scoped_preferences_and_membership(self):
        with self.session_factory() as session:
            session.add_all([
                GroupUserPreference(group_id=20, user_id=self.user_id, platform_id=1, online=True, offline=False),
                GroupUserPreference(group_id=10, user_id=self.user_id, platform_id=1, online=True, offline=False),
                GroupUserPreference(group_id=20, user_id=self.other_user_id, platform_id=1, online=True, offline=False),
            ])
            session.commit()
        self.assertEqual(self.request("/leave_group/", "DELETE", {"group_id": 20}), (200, {
            "user": {"id": str(self.user_id), "name": "Member"},
            "group": {"id": 20, "name": "Friends"},
        }))
        self.assertEqual(self.request("/groups/20")[0], 404)
        with self.session_factory() as session:
            rows = session.query(GroupUserPreference).all()
            self.assertEqual({(row.group_id, row.user_id) for row in rows}, {
                (10, self.user_id), (20, self.other_user_id),
            })

    def test_last_member_leaving_preserves_empty_group(self):
        self.assertEqual(self.request("/leave_group/", "DELETE", {"group_id": 10})[0], 200)
        with self.session_factory() as session:
            self.assertEqual(session.get(Group, 10).users, [])


if __name__ == "__main__":
    unittest.main()
