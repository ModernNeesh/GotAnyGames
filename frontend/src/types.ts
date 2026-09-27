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

export interface GroupPreferencesData {
  platform_ids: number[]
  online: boolean
  offline: boolean
}
