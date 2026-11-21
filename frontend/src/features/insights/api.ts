import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'

export interface Source {
  title: string
  url: string
}

interface Series<Row> {
  unit: string
  rows: Row[]
  sources: Source[]
}

export interface Insights {
  headline: {
    domestic_visits_2024_million: number
    foreign_visits_2024_million: number
    foreign_arrivals_2025_lakh: number
    peak_month: string
    quietest_month: string
  }
  foreign_arrivals_by_month: Series<{ month: string; arrivals: number }> & { year: number }
  domestic_visits_by_state: Series<{ state: string; visits: number }> & { year: number }
  foreign_visits_by_state: Series<{ state: string; visits: number }> & { year: number }
  top_monuments: Series<{
    name: string
    place: string
    domestic_m: number
    foreign_m: number | null
  }> & { period: string }
  foreign_arrivals_by_year: Series<YearRow>
  forex_earnings_by_year: Series<YearRow>
  departures_by_year: Series<YearRow>
  source_countries_2024: Series<{ country: string; value: number }> & { year: number }
  source_countries_2025: Series<{ country: string; value: number }> & { year: number }
  purpose_of_visit: Series<{ label: string; value: number }> & { year: number }
  ports_of_entry: Series<{ label: string; value: number }> & { year: number }
  key_facts: { year: number; rows: { label: string; value: string; note: string }[]; sources: Source[] }
  year_on_year: {
    rows: { indicator: string; y2024: string; y2025: string; change: number }[]
    sources: Source[]
  }
  reports: Report[]
}

export interface YearRow {
  year: number
  value: number
}

export interface Report {
  title: string
  kind: string
  year: number | null
  about: string
  url: string
}

export function useInsights() {
  return useQuery({
    queryKey: ['insights'],
    queryFn: async () => (await api.get<Insights>('/insights')).data,
    staleTime: 24 * 60 * 60 * 1000, // a yearly snapshot
  })
}
