"""Group preference aggregates shared by the API and future recommendations."""

from sqlalchemy import and_, case, func, select
from sqlalchemy.orm import Session

from app.models.db import GroupUserPreference, Platform, group_membership
from app.models.schemas import (
    GroupPlatformPreferenceSummaryModel,
    GroupPreferenceSummaryModel,
)


def summarize_group_preferences(session: Session, group_id: int) -> GroupPreferenceSummaryModel:
    """Summarize current members' choices; callers must enforce access separately.

    Platform percentages include every member, even those without preferences.
    Mode percentages include only members selecting that platform. A member who
    selects both modes contributes to both counts. Keep counts and unrounded
    percentages available to recommendations; the UI handles display rounding.
    """
    total_members = (
        select(func.count())
        .select_from(group_membership)
        .where(group_membership.c.group_id == group_id)
        .correlate(None)
        .scalar_subquery()
    )
    platform_members = func.count(GroupUserPreference.user_id)
    # Read totals and platform counts in one statement for a consistent snapshot.
    # Starting from membership excludes stale preferences belonging to nonmembers;
    # the outer join preserves a total even when nobody has saved preferences.
    rows = (
        session.query(
            total_members.label("total_members"),
            Platform.id.label("platform_id"),
            Platform.name.label("platform_name"),
            platform_members.label("member_count"),
            func.sum(case((GroupUserPreference.online.is_(True), 1), else_=0)).label("online_count"),
            func.sum(case((GroupUserPreference.offline.is_(True), 1), else_=0)).label("offline_count"),
        )
        .select_from(group_membership)
        .outerjoin(GroupUserPreference, and_(
            GroupUserPreference.group_id == group_membership.c.group_id,
            GroupUserPreference.user_id == group_membership.c.user_id,
        ))
        .outerjoin(Platform, Platform.id == GroupUserPreference.platform_id)
        .filter(group_membership.c.group_id == group_id)
        .group_by(Platform.id, Platform.name)
        .order_by(platform_members.desc(), func.lower(Platform.name), Platform.id)
        .all()
    )
    member_count = rows[0].total_members if rows else 0
    return GroupPreferenceSummaryModel(
        member_count=member_count,
        platforms=[
            GroupPlatformPreferenceSummaryModel(
                platform_id=row.platform_id,
                platform_name=row.platform_name,
                member_count=row.member_count,
                member_percentage=100.0 * row.member_count / member_count,
                online_count=row.online_count,
                online_percentage=100.0 * row.online_count / row.member_count,
                offline_count=row.offline_count,
                offline_percentage=100.0 * row.offline_count / row.member_count,
            )
            for row in rows if row.platform_id is not None
        ],
    )
