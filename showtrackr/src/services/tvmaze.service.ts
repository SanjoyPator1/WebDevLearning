import ApiService from './api.service'
import type { Show, SearchResult } from '@/models/Show'
import type { Episode } from '@/models/Episode'

class TVMazeService {
  private apiService: ApiService

  constructor() {
    this.apiService = new ApiService('https://api.tvmaze.com')
  }

  /**
   * Search for TV shows by name
   */
  public async searchShows(query: string): Promise<SearchResult[]> {
    return this.apiService.get<SearchResult[]>(`/search/shows?q=${encodeURIComponent(query)}`)
  }

  /**
   * Get detailed information about a specific show by ID
   */
  public async getShowById(id: number): Promise<Show> {
    return this.apiService.get<Show>(`/shows/${id}`)
  }

  /**
   * Get all episodes for a specific show
   */
  public async getShowEpisodes(showId: number): Promise<Episode[]> {
    return this.apiService.get<Episode[]>(`/shows/${showId}/episodes`)
  }

  /**
   * Get episodes organized by season
   */
  public async getShowEpisodesBySeason(showId: number): Promise<Record<number, Episode[]>> {
    const episodes = await this.getShowEpisodes(showId)

    return episodes.reduce(
      (seasons, episode) => {
        const season = episode.season

        if (!seasons[season]) {
          seasons[season] = []
        }

        seasons[season].push(episode)
        return seasons
      },
      {} as Record<number, Episode[]>,
    )
  }

  /**
   * Get a specific episode by show ID and episode number
   */
  public async getEpisodeByNumber(
    showId: number,
    season: number,
    episode: number,
  ): Promise<Episode> {
    return this.apiService.get<Episode>(
      `/shows/${showId}/episodebynumber?season=${season}&number=${episode}`,
    )
  }

  /**
   * Get show cast information
   */
  public async getShowCast(showId: number): Promise<any[]> {
    return this.apiService.get<any[]>(`/shows/${showId}/cast`)
  }

  /**
   * Get show images
   */
  public async getShowImages(showId: number): Promise<any[]> {
    return this.apiService.get<any[]>(`/shows/${showId}/images`)
  }

  /**
   * Get show seasons
   */
  public async getShowSeasons(showId: number): Promise<any[]> {
    return this.apiService.get<any[]>(`/shows/${showId}/seasons`)
  }
}

// Create and export a singleton instance
export const tvMazeService = new TVMazeService()
