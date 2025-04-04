export interface Episode {
  id: number
  url: string
  name: string
  season: number
  number: number
  type: string
  airdate: string
  airtime: string
  airstamp: string
  runtime: number
  rating: {
    average: number | null
  }
  image: {
    medium: string | null
    original: string | null
  } | null
  summary: string | null
  _links: {
    self: { href: string }
    show?: { href: string }
  }
}

export interface EpisodeBySeason {
  [season: number]: Episode[]
}
