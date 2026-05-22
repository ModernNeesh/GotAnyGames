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
