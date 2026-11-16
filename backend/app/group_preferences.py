"""Group preference aggregates shared by the API and future recommendations."""

from sqlalchemy import and_, case, func, select
from sqlalchemy.orm import Session

from app.models.db import GroupUserPreference, Platform, group_membership
from app.models.schemas import (
    GroupPlatformPreferenceSummaryModel,
    GroupPreferenceSummaryModel,
)


def summarize_group_preferences(session: Session, group_id: int) -> GroupPreferenceSummaryModel:
    """
    Summarizes current members' choices.

    Platform percentages include every member, even those without preferences.
    Mode percentages include only members selecting that platform. 

    Inputs:
    group_id (int): ID of group to summarize


    """
    total_members = (
        select(func.count())
        .select_from(group_membership)
        .where(group_membership.c.group_id == group_id)
        .correlate(None)
        .scalar_subquery()
    ) # Subquery for total members in the group. We avoid extracting the value here because that would require a separate query.


    platform_members = func.count(GroupUserPreference.user_id) # Wrapper function to get count of members who chose each platform

    """
    A query that returns the following data for each platform selected by the group:
    - Number of members that selected the platform
    - Number of users that prefer online play for this platform
    - Number of users that prefer offline play for this platform

    In the double_joined query (before groupby and filter), each row represents one user's preference for one platform in one group
    """
    platform_summaries = (
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
    member_count = platform_summaries[0].total_members if platform_summaries else 0
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
            for row in platform_summaries if row.platform_id is not None
        ],
    )
