export interface UserPreferences {
  isDarkMode: boolean
  sortPreference: SortOption
  filterPreference: FilterOption
}

export type SortOption = 'name' | 'date' | 'rating'
export type FilterOption = 'all' | 'watching' | 'completed' | 'planned'

export interface WatchStatus {
  showId: number
  status: WatchStatusType
  lastWatched?: Date
  progress: number // Percentage completed
}

export type WatchStatusType = 'watching' | 'completed' | 'planned' | 'dropped'
