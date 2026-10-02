export interface SearchbarGameData {
  id: number
  name: string
  total_rating: number
  total_rating_count: number
  cover_url: string
  platforms: string[]
}

export interface UserRatedGame {
  game_id: number
  game_name: string
  cover_url: string
  rating: number
  platforms: string[]
}

export interface UserGroup {
  id: number
  name: string
}

export interface GroupMember {
  id: string
  name: string
}

export interface GroupDetailData extends UserGroup {
  members: GroupMember[]
}

export interface GroupPlatform {
  id: number
  name: string
}

export interface GroupPlatformPreference {
  platform_id: number
  online: boolean
  offline: boolean
}

export interface GroupPreferencesData {
  platforms: GroupPlatformPreference[]
}

export interface GroupPlatformPreferenceSummary {
  platform_id: number
  platform_name: string
  member_count: number
  member_percentage: number
  online_count: number
  online_percentage: number
  offline_count: number
  offline_percentage: number
}

export interface GroupPreferenceSummaryData {
  member_count: number
  platforms: GroupPlatformPreferenceSummary[]
}
