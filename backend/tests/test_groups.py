"""Isolated API coverage for group lists, detail-page actions, and preferences.

Requests run directly through a test FastAPI app and an in-memory SQLite DB.
The production database module is replaced before importing the router, and
get_current_user is overridden to exercise different callers without real
tokens. Clearing the override checks rejection of unauthenticated requests;
these tests do not exercise live Supabase JWT verification or PostgreSQL.

Run from backend: python.exe -m unittest discover -s tests -v
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
from app.group_preferences import summarize_group_preferences
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
        self.assertEqual(self.request("/groups/40/preferences/summary"),
                         self.request("/groups/999/preferences/summary"))
        self.assertEqual(self.request("/groups/40/preferences/summary")[0], 404)

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

    def test_remove_member_returns_detail_and_deletes_only_target_group_membership_and_preferences(self):
        with self.session_factory() as session:
            session.add_all([
                GroupUserPreference(group_id=20, user_id=self.other_user_id, platform_id=1, online=True, offline=False),
                GroupUserPreference(group_id=20, user_id=self.other_user_id, platform_id=2, online=False, offline=True),
                GroupUserPreference(group_id=40, user_id=self.other_user_id, platform_id=1, online=False, offline=True),
                GroupUserPreference(group_id=20, user_id=self.user_id, platform_id=1, online=True, offline=True),
                UserPref(user_id=self.other_user_id, platform_id=1, online=True, offline=False),
            ])
            session.commit()
        self.assertEqual(self.request(f"/groups/20/members/{self.other_user_id}", "DELETE"), (200, {
            "id": 20,
            "name": "Friends",
            "members": [{"id": str(self.user_id), "name": "Member"}],
        }))
        self.assertEqual(self.request(f"/groups/20/members/{self.other_user_id}/preferences")[0], 404)
        with self.session_factory() as session:
            self.assertEqual({(row.group_id, row.user_id, row.platform_id, row.online, row.offline)
                              for row in session.query(GroupUserPreference).all()}, {
                (40, self.other_user_id, 1, False, True),
                (20, self.user_id, 1, True, True),
            })
            self.assertEqual({(row.group_id, row.user_id) for row in session.execute(group_membership.select())}, {
                (10, self.user_id), (20, self.user_id), (30, self.user_id), (40, self.other_user_id),
            })
            self.assertEqual(session.get(User, self.other_user_id).name, "Other")
            self.assertEqual(session.query(User).count(), 3)
            self.assertEqual([(row.platform_id, row.online, row.offline)
                              for row in session.query(UserPref).filter_by(user_id=self.other_user_id)],
                             [(1, True, False)])
        self.app.dependency_overrides[get_current_user] = lambda: self.other_user_id
        self.assertEqual(self.request("/groups/20")[0], 404)
        self.assertEqual(self.request("/groups/40")[0], 200)

    def test_new_member_can_remove_the_group_creator(self):
        status, created = self.request("/create_group/", "POST", {"name": "Shared group"})
        self.assertEqual(status, 200)
        group_id = created["id"]
        self.assertEqual(self.request(f"/groups/{group_id}/members", "POST", {
            "user_id": str(self.other_user_id),
        })[0], 200)
        self.app.dependency_overrides[get_current_user] = lambda: self.other_user_id
        self.assertEqual(self.request(f"/groups/{group_id}/members/{self.user_id}", "DELETE"), (200, {
            "id": group_id,
            "name": "Shared group",
            "members": [{"id": str(self.other_user_id), "name": "Other"}],
        }))

    def test_remove_member_rejects_self_missing_group_nonmember_and_invalid_uuid(self):
        detail = self.request("/groups/20")
        self.assertEqual(self.request(f"/groups/20/members/{self.user_id}", "DELETE")[0], 400)
        for path in [
            f"/groups/999/members/{self.other_user_id}",
            f"/groups/20/members/{self.third_user_id}",
            f"/groups/20/members/{UUID(int=999)}",
        ]:
            with self.subTest(path=path):
                self.assertEqual(self.request(path, "DELETE")[0], 404)
        self.assertEqual(self.request("/groups/20/members/not-a-uuid", "DELETE")[0], 422)
        self.assertEqual(self.request("/groups/20"), detail)

    def test_member_removal_rolls_back_preferences_and_membership_on_commit_failure(self):
        with self.session_factory() as session:
            session.add(GroupUserPreference(
                group_id=20, user_id=self.other_user_id, platform_id=1, online=True, offline=False,
            ))
            session.commit()

        def fail_commit(session):
            session.flush()
            raise RuntimeError("Simulated database commit failure")

        with patch.object(self.session_factory.class_, "commit", fail_commit):
            with self.assertRaisesRegex(RuntimeError, "Simulated database commit failure"):
                self.request(f"/groups/20/members/{self.other_user_id}", "DELETE")
        self.assertEqual(self.request("/groups/20")[1]["members"], [
            {"id": str(self.user_id), "name": "Member"},
            {"id": str(self.other_user_id), "name": "Other"},
        ])
        self.assertEqual(self.request(f"/groups/20/members/{self.other_user_id}/preferences"), (200, {
            "platforms": [{"platform_id": 1, "online": True, "offline": False}],
        }))

    def test_platform_catalog_is_authenticated_and_sorted(self):
        self.assertEqual(self.request("/group_platforms/"), (200, [
            {"id": 2, "name": "Nintendo Switch"}, {"id": 1, "name": "PC"},
        ]))

    def test_default_preferences_are_empty_and_only_members_are_visible(self):
        self.assertEqual(self.request(f"/groups/20/members/{self.other_user_id}/preferences"), (200, {
            "platforms": [],
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
        payload = {"platforms": [{"platform_id": 2, "online": False, "offline": True}]}
        self.assertEqual(self.request("/groups/20/preferences", "PATCH", payload), (200, payload))
        self.assertEqual(self.request(f"/groups/20/members/{self.user_id}/preferences"), (200, payload))
        original = {"platforms": [{"platform_id": 1, "online": True, "offline": False}]}
        self.assertEqual(self.request(f"/groups/10/members/{self.user_id}/preferences"), (200, original))
        self.assertEqual(self.request(f"/groups/20/members/{self.other_user_id}/preferences"), (200, original))
        with self.session_factory() as session:
            prefs = session.query(UserPref).filter_by(user_id=self.user_id).all()
            self.assertEqual([(row.platform_id, row.online, row.offline) for row in prefs], [(1, True, False)])

    def test_preferences_validate_platforms_and_modes_without_erasing_saved_values(self):
        online_platform = {"platform_id": 1, "online": True, "offline": False}
        original = {"platforms": [online_platform]}
        self.assertEqual(self.request("/groups/20/preferences", "PATCH", original)[0], 200)
        invalid_platforms = [
            [],
            [online_platform, {**online_platform, "online": False, "offline": True}],
            *[[{**online_platform, "platform_id": platform_id}] for platform_id in [0, -1, True, "1", 1.0]],
            [online_platform, {**online_platform, "platform_id": 999}],
            [online_platform, {"platform_id": 2, "online": False, "offline": False}],
            *[[{**online_platform, mode: value}] for mode in ["online", "offline"] for value in ["yes", 1, None]],
            [{"platform_id": 1, "online": True}],
            [{"platform_id": 1, "offline": True}],
            [{**online_platform, "user_id": str(self.other_user_id)}],
            [{**online_platform, "unexpected": True}],
        ]
        invalid_payloads = [{"platforms": platforms} for platforms in invalid_platforms] + [
            {},
            {"platforms": None},
            {**original, "user_id": str(self.other_user_id)},
            {**original, "online": True},
            {"platform_ids": [1], "online": True, "offline": False},
        ]
        for payload in invalid_payloads:
            with self.subTest(payload=payload):
                self.assertEqual(self.request("/groups/20/preferences", "PATCH", payload)[0], 422)
                self.assertEqual(self.request(f"/groups/20/members/{self.user_id}/preferences"), (200, original))

    def test_multi_platform_preferences_preserve_independent_modes_in_id_order(self):
        payload = {"platforms": [
            {"platform_id": 2, "online": False, "offline": True},
            {"platform_id": 1, "online": True, "offline": False},
        ]}
        expected = {"platforms": list(reversed(payload["platforms"]))}
        self.assertEqual(self.request("/groups/20/preferences", "PATCH", payload), (200, expected))
        self.assertEqual(self.request(f"/groups/20/members/{self.user_id}/preferences"), (200, expected))
        self.app.dependency_overrides[get_current_user] = lambda: self.other_user_id
        self.assertEqual(self.request(f"/groups/20/members/{self.user_id}/preferences"), (200, expected))
        with self.session_factory() as session:
            rows = session.query(GroupUserPreference).filter_by(group_id=20, user_id=self.user_id).all()
            self.assertEqual({(row.platform_id, row.online, row.offline) for row in rows}, {
                (1, True, False), (2, False, True),
            })

    def test_platform_can_select_both_modes_independently_of_other_platforms(self):
        payload = {"platforms": [
            {"platform_id": 1, "online": True, "offline": True},
            {"platform_id": 2, "online": False, "offline": True},
        ]}
        self.assertEqual(self.request("/groups/20/preferences", "PATCH", payload), (200, payload))
        self.assertEqual(self.request(f"/groups/20/members/{self.user_id}/preferences"), (200, payload))

    def test_existing_preference_rows_keep_their_individual_modes(self):
        with self.session_factory() as session:
            session.add_all([
                GroupUserPreference(group_id=20, user_id=self.user_id, platform_id=2, online=False, offline=True),
                GroupUserPreference(group_id=20, user_id=self.user_id, platform_id=1, online=True, offline=False),
            ])
            session.commit()
        self.assertEqual(self.request(f"/groups/20/members/{self.user_id}/preferences"), (200, {
            "platforms": [
                {"platform_id": 1, "online": True, "offline": False},
                {"platform_id": 2, "online": False, "offline": True},
            ],
        }))

    def test_nonmembers_cannot_read_search_add_remove_edit_or_leave_group(self):
        for path, method, payload, query in [
            ("/groups/40", "GET", None, b""),
            ("/groups/40/users", "GET", None, b"query=Third"),
            ("/groups/40/members", "POST", {"user_id": str(self.user_id)}, b""),
            (f"/groups/40/members/{self.other_user_id}", "DELETE", None, b""),
            (f"/groups/40/members/{self.other_user_id}/preferences", "GET", None, b""),
            ("/groups/40/preferences/summary", "GET", None, b""),
            ("/groups/40/preferences", "PATCH", {"platforms": [{"platform_id": 1, "online": True, "offline": False}]}, b""),
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
            (f"/groups/20/members/{self.other_user_id}", "DELETE", None, b""),
            (f"/groups/20/members/{self.user_id}/preferences", "GET", None, b""),
            ("/groups/20/preferences/summary", "GET", None, b""),
            ("/groups/20/preferences", "PATCH", {"platforms": [{"platform_id": 1, "online": True, "offline": False}]}, b""),
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


class GroupPreferenceSummaryTests(unittest.TestCase):
    """Check aggregate preferences against current membership and saved modes."""

    def setUp(self):
        GroupDetailTests.setUp(self)

    def request(self, path, method="GET", payload=None, query_string=b""):
        return GroupDetailTests.request(self, path, method, payload, query_string)

    def test_summary_uses_platform_union_and_counts_members_without_preferences(self):
        with self.session_factory() as session:
            session.get(Group, 20).users.append(session.get(User, self.third_user_id))
            session.add_all([
                Platform(id=3, name="arcade"), Platform(id=4, name="Arcade"),
                Platform(id=5, name="Unused"),
                GroupUserPreference(group_id=20, user_id=self.user_id, platform_id=1, online=True, offline=False),
                GroupUserPreference(group_id=20, user_id=self.other_user_id, platform_id=1, online=False, offline=True),
                GroupUserPreference(group_id=20, user_id=self.other_user_id, platform_id=2, online=True, offline=True),
                GroupUserPreference(group_id=20, user_id=self.user_id, platform_id=3, online=True, offline=False),
                GroupUserPreference(group_id=20, user_id=self.other_user_id, platform_id=4, online=False, offline=True),
            ])
            session.commit()
        status, body = self.request("/groups/20/preferences/summary")
        self.assertEqual(status, 200)
        self.assertEqual(body["member_count"], 3)
        self.assertEqual([
            (row["platform_id"], row["platform_name"], row["member_count"], row["online_count"], row["offline_count"])
            for row in body["platforms"]
        ], [
            (1, "PC", 2, 1, 1),
            (3, "arcade", 1, 1, 0),
            (4, "Arcade", 1, 0, 1),
            (2, "Nintendo Switch", 1, 1, 1),
        ])
        expected_percentages = [(200 / 3, 50, 50), (100 / 3, 100, 0),
                                (100 / 3, 0, 100), (100 / 3, 100, 100)]
        for row, percentages in zip(body["platforms"], expected_percentages):
            with self.subTest(platform_id=row["platform_id"]):
                for field, expected in zip(
                    ["member_percentage", "online_percentage", "offline_percentage"], percentages,
                ):
                    self.assertAlmostEqual(row[field], expected)

    def test_summary_mode_percentages_are_unrounded_and_count_both_modes_independently(self):
        with self.session_factory() as session:
            session.get(Group, 20).users.append(session.get(User, self.third_user_id))
            session.add_all([
                GroupUserPreference(group_id=20, user_id=self.user_id, platform_id=1, online=True, offline=True),
                GroupUserPreference(group_id=20, user_id=self.other_user_id, platform_id=1, online=True, offline=False),
                GroupUserPreference(group_id=20, user_id=self.third_user_id, platform_id=1, online=False, offline=True),
            ])
            session.commit()
        status, body = self.request("/groups/20/preferences/summary")
        self.assertEqual(status, 200)
        self.assertEqual(body["member_count"], 3)
        self.assertEqual(len(body["platforms"]), 1)
        platform = body["platforms"][0]
        self.assertEqual(platform["member_count"], 3)
        self.assertEqual(platform["member_percentage"], 100)
        self.assertEqual(platform["online_count"], 2)
        self.assertEqual(platform["offline_count"], 2)
        self.assertAlmostEqual(platform["online_percentage"], 200 / 3)
        self.assertAlmostEqual(platform["offline_percentage"], 200 / 3)

    def test_summary_excludes_nonmember_rows_other_groups_and_global_preferences(self):
        with self.session_factory() as session:
            session.add_all([
                GroupUserPreference(group_id=20, user_id=self.user_id, platform_id=1, online=False, offline=True),
                GroupUserPreference(group_id=20, user_id=self.third_user_id, platform_id=1, online=True, offline=True),
                GroupUserPreference(group_id=20, user_id=self.third_user_id, platform_id=2, online=True, offline=True),
                GroupUserPreference(group_id=10, user_id=self.user_id, platform_id=2, online=True, offline=True),
                GroupUserPreference(group_id=40, user_id=self.other_user_id, platform_id=2, online=True, offline=True),
                UserPref(user_id=self.other_user_id, platform_id=2, online=True, offline=True),
            ])
            session.commit()
        self.assertEqual(self.request("/groups/20/preferences/summary"), (200, {
            "member_count": 2,
            "platforms": [{
                "platform_id": 1, "platform_name": "PC", "member_count": 1, "member_percentage": 50,
                "online_count": 0, "online_percentage": 0, "offline_count": 1, "offline_percentage": 100,
            }],
        }))

    def test_summary_handles_no_preferences_and_one_or_zero_members(self):
        self.assertEqual(self.request("/groups/20/preferences/summary"), (200, {
            "member_count": 2, "platforms": [],
        }))
        self.assertEqual(self.request("/groups/10/preferences/summary"), (200, {
            "member_count": 1, "platforms": [],
        }))
        self.assertEqual(self.request("/groups/10/preferences", "PATCH", {
            "platforms": [{"platform_id": 2, "online": True, "offline": True}],
        })[0], 200)
        expected = {
            "member_count": 1,
            "platforms": [{
                "platform_id": 2, "platform_name": "Nintendo Switch", "member_count": 1, "member_percentage": 100,
                "online_count": 1, "online_percentage": 100, "offline_count": 1, "offline_percentage": 100,
            }],
        }
        self.assertEqual(self.request("/groups/10/preferences/summary"), (200, expected))
        with self.session_factory() as session:
            self.assertEqual(summarize_group_preferences(session, 10).model_dump(), expected)
        self.assertEqual(self.request("/leave_group/", "DELETE", {"group_id": 10})[0], 200)
        with self.session_factory() as session:
            self.assertEqual(summarize_group_preferences(session, 10).model_dump(), {
                "member_count": 0, "platforms": [],
            })
        self.assertEqual(self.request("/groups/10/preferences/summary")[0], 404)

    def test_summary_refreshes_after_preference_replacement_add_remove_and_leave(self):
        def summary():
            status, body = self.request("/groups/20/preferences/summary")
            self.assertEqual(status, 200)
            return body

        def save(platform_id, online, offline):
            self.assertEqual(self.request("/groups/20/preferences", "PATCH", {
                "platforms": [{"platform_id": platform_id, "online": online, "offline": offline}],
            })[0], 200)

        save(1, True, False)
        initial = summary()
        self.assertEqual(initial["member_count"], 2)
        self.assertEqual(initial["platforms"][0]["member_percentage"], 50)
        save(2, False, True)
        replaced = summary()["platforms"]
        self.assertEqual([row["platform_id"] for row in replaced], [2])
        self.assertEqual((replaced[0]["online_count"], replaced[0]["offline_count"]), (0, 1))

        self.assertEqual(self.request("/groups/20/members", "POST", {"user_id": str(self.third_user_id)})[0], 200)
        added = summary()
        self.assertEqual(added["member_count"], 3)
        self.assertAlmostEqual(added["platforms"][0]["member_percentage"], 100 / 3)
        self.app.dependency_overrides[get_current_user] = lambda: self.third_user_id
        save(1, True, True)
        self.app.dependency_overrides[get_current_user] = lambda: self.user_id
        self.assertEqual({row["platform_id"] for row in summary()["platforms"]}, {1, 2})
        self.assertEqual(self.request(f"/groups/20/members/{self.third_user_id}", "DELETE")[0], 200)
        removed = summary()
        self.assertEqual(removed["member_count"], 2)
        self.assertEqual([row["platform_id"] for row in removed["platforms"]], [2])
        self.assertEqual(removed["platforms"][0]["member_percentage"], 50)

        self.assertEqual(self.request("/leave_group/", "DELETE", {"group_id": 20})[0], 200)
        self.app.dependency_overrides[get_current_user] = lambda: self.other_user_id
        self.assertEqual(summary(), {"member_count": 1, "platforms": []})


if __name__ == "__main__":
    unittest.main()
