"""Recommendation helper and HTTP coverage without production DB/auth access.

The helper executes real SQL against SQLite. HTTP tests use the application's
registered routes, with isolated sessions and a stub for the PostgreSQL-specific
full-game loader (array_agg). Supabase JWT verification is not exercised.

Run from backend: ..\\.venv\\Scripts\\python.exe -m unittest discover -s tests -v
"""

import asyncio
import sys
import unittest
from types import ModuleType
from unittest.mock import patch
from uuid import UUID

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth import get_current_user
from app.models.db import (
    Base, Game, Group, GroupUserPreference, MultiplayerMode, Platform, User,
    UserPref, UserRating,
)
from app.models.schemas import FullGameData
from test_groups import get_response  # Also registers SQLite's UUID compiler.


test_database = ModuleType("app.database")
test_database.Session = None
with patch.dict(sys.modules, {"app.database": test_database}):
    from app import main
    from app.routers import recs


class RecommendationFixture(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.addCleanup(self.engine.dispose)
        self.session_factory = sessionmaker(bind=self.engine)
        self.user_id, self.friend_id, self.outsider_id = [UUID(int=i) for i in (1, 2, 3)]
        with self.session_factory() as session:
            member = User(id=self.user_id, name="Member")
            friend = User(id=self.friend_id, name="Friend")
            outsider = User(id=self.outsider_id, name="Outsider")
            session.add_all([
                Group(id=10, name="Friends", users=[member, friend]),
                Group(id=20, name="Private", users=[outsider]),
                Group(id=30, name="Empty"),
                Group(id=40, name="Solo", users=[member]),
                *[Platform(id=i, name=f"Platform {i}") for i in range(1, 6)],
            ])
            session.commit()

    def preferences(self, *rows, group_id=10):
        with self.session_factory() as session:
            session.add_all([
                GroupUserPreference(
                    group_id=group_id, user_id=user_id, platform_id=platform_id,
                    online=online, offline=offline,
                )
                for user_id, platform_id, online, offline in rows
            ])
            session.commit()

    def game(self, game_id, *, ratings=(8, 9), platform_ids=(1,), modes=None):
        if modes is None:
            modes = [{"platform": platform_ids[0], "onlinecoopmax": 4}]
        with self.session_factory() as session:
            session.add(Game(
                id=game_id, name=f"Game {game_id}",
                platforms=[session.get(Platform, platform_id) for platform_id in platform_ids],
                multiplayer_modes=[MultiplayerMode(**{
                    "dropin": False, "campaigncoop": False, "splitscreen": False,
                    "onlinecoopmax": 0, "onlinepvpmax": 0,
                    "offlinecoopmax": 0, "offlinepvpmax": 0, **mode,
                }) for mode in modes],
            ))
            session.add_all([
                UserRating(user_id=user_id, game_id=game_id, rating=rating)
                for user_id, rating in zip((self.user_id, self.friend_id, self.outsider_id), ratings)
                if rating is not None
            ])
            session.commit()

    def recommend(self, group_id=10, num_games=1):
        with self.session_factory() as session:
            return recs.get_recommendations_for_group(session, group_id, num_games)


class RecommendationHelperTests(RecommendationFixture):
    def test_ranks_by_group_average_limits_results_and_breaks_ties_by_game_id(self):
        self.preferences((self.user_id, 1, True, False))
        self.game(4, ratings=(9, 10))
        self.game(1, ratings=(9, 10))
        self.game(2, ratings=(8, 8))
        self.game(3, ratings=(8, 9))
        self.assertEqual(self.recommend(), (10, [1], [9.5]))
        self.assertEqual(self.recommend(num_games=3), (10, [1, 4, 3], [9.5, 9.5, 8.5]))

    def test_requires_every_current_member_to_rate_and_ignores_outsider_ratings(self):
        self.preferences((self.user_id, 1, True, False))
        self.game(1, ratings=(9, 8, 1))
        self.game(2, ratings=(10, None, 10))
        self.game(3, ratings=(None, None, 10))
        self.assertEqual(self.recommend(num_games=3), (10, [1], [8.5]))

    def test_chooses_three_most_popular_platforms(self):
        self.preferences(
            (self.user_id, 1, True, False),
            (self.user_id, 2, True, False),
            (self.user_id, 3, True, False),
            (self.user_id, 4, True, False),
            (self.friend_id, 4, True, False),
        )
        self.game(1, platform_ids=(4,))
        self.assertEqual(self.recommend(), (10, [1], [8.5]))

    def test_platform_ties_prioritize_stronger_play_mode_agreement(self):
        self.preferences(
            (self.user_id, 1, True, False), (self.friend_id, 1, False, True),
            *[(member, platform, True, False)
              for platform in (2, 3, 4) for member in (self.user_id, self.friend_id)],
        )
        self.game(1, platform_ids=(1,), ratings=(10, 10))
        self.game(2, platform_ids=(4,))
        self.assertEqual(self.recommend(num_games=3), (10, [2], [8.5]))

    def test_excludes_platforms_outside_top_three(self):
        self.preferences(
            *[(member, platform, True, False)
              for platform in (1, 2, 3) for member in (self.user_id, self.friend_id)],
            (self.user_id, 4, True, False),
        )
        self.game(1, platform_ids=(4,), ratings=(10, 10))
        self.game(2, platform_ids=(1,))
        self.assertEqual(self.recommend(num_games=3), (10, [2], [8.5]))

    def test_online_preference_accepts_coop_or_pvp_with_two_or_more_players(self):
        self.preferences((self.user_id, 1, True, False))
        self.game(1, modes=[{"platform": 1, "onlinecoopmax": 2}])
        self.game(2, modes=[{"platform": 1, "onlinepvpmax": 2}])
        self.game(3, modes=[{"platform": 1, "offlinecoopmax": 4}])
        self.game(4, modes=[{"platform": 1, "onlinecoopmax": 1, "onlinepvpmax": 1}])
        self.assertEqual(self.recommend(num_games=3), (10, [1, 2], [8.5, 8.5]))

    def test_offline_majority_accepts_coop_or_pvp_and_rejects_online_only(self):
        self.preferences(
            (self.user_id, 1, False, True), (self.friend_id, 1, True, True),
        )
        self.game(1, modes=[{"platform": 1, "offlinecoopmax": 2}])
        self.game(2, modes=[{"platform": 1, "offlinepvpmax": 2}])
        self.game(3)
        self.assertEqual(self.recommend(num_games=3), (10, [1, 2], [8.5, 8.5]))

    def test_play_mode_ties_choose_online(self):
        self.preferences((self.user_id, 1, True, True))
        self.game(1)
        self.game(2, modes=[{"platform": 1, "offlinecoopmax": 4}])
        self.assertEqual(self.recommend(num_games=3), (10, [1], [8.5]))

    def test_play_mode_must_match_the_preference_on_the_same_platform(self):
        self.preferences(
            (self.user_id, 1, True, False), (self.user_id, 2, False, True),
        )
        self.game(1, platform_ids=(1, 2), modes=[
            {"platform": 1, "offlinecoopmax": 4},
            {"platform": 2, "onlinecoopmax": 4},
        ])
        self.game(2, platform_ids=(1, 2), modes=[{"platform": 2, "offlinecoopmax": 2}])
        self.game(3, platform_ids=(1, 3), modes=[{"platform": 3, "onlinecoopmax": 4}])
        self.assertEqual(self.recommend(num_games=3), (10, [2], [8.5]))

    def test_qualifying_modes_do_not_duplicate_games(self):
        self.preferences((self.user_id, 1, True, False), (self.user_id, 2, True, False))
        self.game(1, platform_ids=(1, 2), modes=[
            {"platform": 1, "onlinecoopmax": 4}, {"platform": 2, "onlinepvpmax": 2},
        ])
        self.assertEqual(self.recommend(num_games=3), (10, [1], [8.5]))

    def test_no_members_preferences_ratings_or_matching_modes_return_empty(self):
        self.assertEqual(self.recommend(group_id=30), (30, [], []))
        self.assertEqual(self.recommend(group_id=999), (999, [], []))
        self.assertEqual(self.recommend(), (10, [], []))
        self.preferences((self.user_id, 1, True, False))
        self.assertEqual(self.recommend(), (10, [], []))
        self.game(1, modes=[])
        self.assertEqual(self.recommend(), (10, [], []))

    def test_single_member_group_can_receive_multiplayer_recommendation(self):
        self.preferences((self.user_id, 1, True, False), group_id=40)
        self.game(1, ratings=(9, None))
        self.assertEqual(self.recommend(group_id=40), (40, [1], [9.0]))

    def test_preferences_from_other_groups_nonmembers_and_global_settings_are_ignored(self):
        self.preferences((self.user_id, 1, True, False))
        self.preferences((self.outsider_id, 2, True, False))
        self.preferences((self.user_id, 2, True, False), group_id=40)
        with self.session_factory() as session:
            session.add(UserPref(user_id=self.user_id, platform_id=2, online=True, offline=False))
            session.commit()
        self.game(1)
        self.game(2, platform_ids=(2,), ratings=(10, 10))
        self.assertEqual(self.recommend(num_games=3), (10, [1], [8.5]))


class RecommendationRouteTests(RecommendationFixture):
    def setUp(self):
        super().setUp()
        session_patch = patch.object(recs, "Session", self.session_factory)
        session_patch.start()
        self.addCleanup(session_patch.stop)
        self.app = main.app
        self.app.dependency_overrides[get_current_user] = lambda: self.user_id
        self.addCleanup(self.app.dependency_overrides.clear)
        loader_patch = patch.object(recs, "pull_game_data")
        self.loader = loader_patch.start()
        self.addCleanup(loader_patch.stop)

    def request(self, group_id=10, query_string=b""):
        return asyncio.run(get_response(
            self.app, query_string, path=f"/get_recs/{group_id}",
        ))

    @staticmethod
    def full_game(game_id=1, platform="Platform 1"):
        return FullGameData(
            id=game_id, name=f"Game {game_id}", total_rating=80.0,
            total_rating_count=10, summary="A multiplayer game.",
            cover_url="https://example.com/cover.jpg", dropin=False,
            campaigncoop=True, offlinecoopmax=0, offlinepvpmax=0,
            onlinecoopmax=4, onlinepvpmax=0, splitscreen=False,
            platforms=[platform], genres=["Adventure"], game_modes=["Co-operative"],
        )

    def test_route_is_registered_in_the_production_app(self):
        self.assertIn("/get_recs/{group_id}", self.app.openapi()["paths"])

    def test_returns_full_game_data_and_fractional_group_average(self):
        self.preferences((self.user_id, 1, True, False))
        self.game(1)
        game = self.full_game()
        self.loader.return_value = [game]
        self.assertEqual(self.request(), (200, {
            "group_id": 10, "games": [game.model_dump(mode="json")], "ratings": [8.5],
        }))
        self.assertEqual(self.loader.call_args.kwargs["game_id"], 1)

    def test_each_full_game_mode_has_its_corresponding_rating(self):
        self.preferences((self.user_id, 1, True, False))
        self.game(1)
        modes = [self.full_game(platform=f"Platform {i}") for i in range(1, 5)]
        self.loader.return_value = modes
        self.assertEqual(self.request(), (200, {
            "group_id": 10, "games": [mode.model_dump(mode="json") for mode in modes],
            "ratings": [8.5] * 4,
        }))

    def test_no_recommendations_returns_empty_lists_without_loading_games(self):
        self.assertEqual(self.request(), (200, {"group_id": 10, "games": [], "ratings": []}))
        self.loader.assert_not_called()

    def test_missing_or_nonmember_groups_return_identical_404s_without_computing(self):
        with patch.object(recs, "get_recommendations_for_group") as helper:
            for group_id in (20, 30, 999):
                with self.subTest(group_id=group_id):
                    self.assertEqual(self.request(group_id), (404, {"detail": "Group not found"}))
            helper.assert_not_called()
        self.loader.assert_not_called()

    def test_unauthenticated_requests_are_rejected_before_computing(self):
        self.app.dependency_overrides.clear()
        with patch.object(recs, "get_recommendations_for_group") as helper:
            status, _ = self.request()
            self.assertIn(status, (401, 403))
            helper.assert_not_called()
        self.loader.assert_not_called()

    def test_user_id_query_parameter_cannot_override_authenticated_identity(self):
        self.app.dependency_overrides[get_current_user] = lambda: self.outsider_id
        with patch.object(recs, "get_recommendations_for_group") as helper:
            self.assertEqual(self.request(query_string=f"user_id={self.user_id}".encode()),
                             (404, {"detail": "Group not found"}))
            helper.assert_not_called()

    def test_invalid_group_id_is_rejected(self):
        self.assertEqual(self.request("invalid")[0], 422)
        self.loader.assert_not_called()


if __name__ == "__main__":
    unittest.main()
