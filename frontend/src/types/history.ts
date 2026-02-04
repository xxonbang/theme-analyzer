export interface HistoryEntry {
  filename: string
  date: string      // "2026-02-04"
  time: string      // "09:30"
  path: string      // "data/history/2026-02-04_0930.json"
}

export interface HistoryIndex {
  updated_at: string
  entries: HistoryEntry[]
}

export interface GroupedHistory {
  date: string
  entries: HistoryEntry[]
}
