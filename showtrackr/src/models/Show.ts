export interface Show {
  id: number
  name: string
  type: string
  language: string
  genres: string[]
  status: string
  runtime: number | null
  averageRuntime: number | null
  premiered: string | null
  ended: string | null
  officialSite: string | null
  schedule: {
    time: string
    days: string[]
  }
  rating: {
    average: number | null
  }
  weight: number
  network: Network | null
  webChannel: Network | null
  dvdCountry: string | null
  externals: {
    tvrage: number | null
    thetvdb: number | null
    imdb: string | null
  }
  image: {
    medium: string | null
    original: string | null
  } | null
  summary: string | null
  updated: number
  _links: {
    self: { href: string }
    previousepisode?: { href: string }
    nextepisode?: { href: string }
  }
}

export interface Network {
  id: number
  name: string
  country: {
    name: string
    code: string
    timezone: string
  } | null
  officialSite: string | null
}

export interface SearchResult {
  score: number
  show: Show
}
