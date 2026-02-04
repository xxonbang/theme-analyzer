import { useState } from "react"
import { BarChart3, RefreshCw, LayoutGrid, List, Calendar, Clock } from "lucide-react"

interface HeaderProps {
  timestamp?: string
  onRefresh?: () => void
  loading?: boolean
  compactMode?: boolean
  onToggleCompact?: () => void
}

export function Header({ timestamp, onRefresh, loading, compactMode, onToggleCompact }: HeaderProps) {
  const [showTooltip, setShowTooltip] = useState(false)

  // 타임스탬프 파싱: "2026-02-03 23:04:50"
  const parseTimestamp = (ts: string) => {
    if (!ts) return null
    const [date, time] = ts.split(" ")
    if (!date || !time) return null

    const [year, month, day] = date.split("-")
    const [hour, minute] = time.split(":")

    return {
      year,
      month,
      day,
      hour,
      minute,
      weekday: getWeekday(year, month, day),
      fullDate: `${year}.${month}.${day}`,
      fullTime: `${hour}:${minute}`,
      shortDate: `${month}.${day}`,
    }
  }

  // 요일 계산
  const getWeekday = (year: string, month: string, day: string) => {
    const weekdays = ["일", "월", "화", "수", "목", "금", "토"]
    const date = new Date(parseInt(year), parseInt(month) - 1, parseInt(day))
    return weekdays[date.getDay()]
  }

  // 상대 시간 계산
  const getRelativeTime = (ts: string) => {
    if (!ts) return ""
    const [date, time] = ts.split(" ")
    if (!date || !time) return ""

    const [year, month, day] = date.split("-")
    const [hour, minute, second] = time.split(":")
    const timestamp = new Date(
      parseInt(year),
      parseInt(month) - 1,
      parseInt(day),
      parseInt(hour),
      parseInt(minute),
      parseInt(second || "0")
    )

    const now = new Date()
    const diffMs = now.getTime() - timestamp.getTime()
    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMs / 3600000)
    const diffDays = Math.floor(diffMs / 86400000)

    if (diffMins < 1) return "방금 전"
    if (diffMins < 60) return `${diffMins}분 전`
    if (diffHours < 24) return `${diffHours}시간 전`
    if (diffDays < 7) return `${diffDays}일 전`
    return null // 7일 이상은 절대 시간 표시
  }

  const parsed = timestamp ? parseTimestamp(timestamp) : null
  const relativeTime = timestamp ? getRelativeTime(timestamp) : null

  return (
    <header className="sticky top-0 z-50 w-full border-b bg-card/95 backdrop-blur supports-[backdrop-filter]:bg-card/80 shadow-sm">
      <div className="container flex h-14 sm:h-16 items-center justify-between px-3 sm:px-4">
        {/* Logo & Title */}
        <div className="flex items-center gap-2 sm:gap-3">
          <div className="flex items-center justify-center w-8 h-8 sm:w-10 sm:h-10 rounded-lg bg-gradient-to-br from-primary to-primary/80 text-primary-foreground shadow-sm">
            <BarChart3 className="w-4 h-4 sm:w-5 sm:h-5" />
          </div>
          <div>
            <h1 className="font-bold text-sm sm:text-lg tracking-tight">Stock TOP10</h1>
            <p className="text-[10px] sm:text-xs text-muted-foreground hidden xs:block">거래량 + 등락률 교차 분석</p>
          </div>
        </div>

        {/* Right Controls */}
        <div className="flex items-center gap-2 sm:gap-3">
          {/* Timestamp Badge - Modern Pill Design */}
          {parsed && (
            <div
              className="relative"
              onMouseEnter={() => setShowTooltip(true)}
              onMouseLeave={() => setShowTooltip(false)}
            >
              {/* Main Badge */}
              <div className="flex items-center gap-1.5 px-2.5 py-1.5 sm:px-3 sm:py-2 rounded-full bg-gradient-to-r from-muted/80 to-muted/50 border border-border/50 shadow-sm cursor-default">
                {/* Live Indicator Dot */}
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
                </span>

                {/* Date & Time Display */}
                <div className="flex items-center gap-1.5 sm:gap-2">
                  {/* Date */}
                  <div className="flex items-center gap-1">
                    <Calendar className="w-3 h-3 text-muted-foreground hidden sm:block" />
                    <span className="text-[10px] sm:text-xs font-medium">
                      <span className="hidden sm:inline">{parsed.fullDate}</span>
                      <span className="sm:hidden">{parsed.shortDate}</span>
                      <span className="text-muted-foreground ml-0.5">({parsed.weekday})</span>
                    </span>
                  </div>

                  {/* Divider */}
                  <span className="w-px h-3 bg-border/70 hidden sm:block"></span>

                  {/* Time */}
                  <div className="flex items-center gap-1">
                    <Clock className="w-3 h-3 text-muted-foreground hidden sm:block" />
                    <span className="text-[10px] sm:text-xs font-semibold tabular-nums">{parsed.fullTime}</span>
                  </div>
                </div>
              </div>

              {/* Tooltip - Relative Time */}
              {showTooltip && relativeTime && (
                <div className="absolute top-full left-1/2 -translate-x-1/2 mt-2 px-2.5 py-1.5 bg-popover text-popover-foreground text-xs font-medium rounded-md shadow-lg border border-border whitespace-nowrap z-50">
                  <span className="text-green-500">●</span> {relativeTime} 업데이트
                  {/* Arrow */}
                  <div className="absolute -top-1 left-1/2 -translate-x-1/2 w-2 h-2 bg-popover border-l border-t border-border rotate-45"></div>
                </div>
              )}
            </div>
          )}

          {/* Compact Mode Toggle */}
          {onToggleCompact && (
            <button
              onClick={onToggleCompact}
              className="flex items-center justify-center w-8 h-8 sm:w-9 sm:h-9 rounded-full bg-secondary/80 hover:bg-secondary transition-all hover:scale-105 active:scale-95"
              title={compactMode ? "상세 보기" : "간단 보기"}
            >
              {compactMode ? (
                <LayoutGrid className="w-4 h-4" />
              ) : (
                <List className="w-4 h-4" />
              )}
            </button>
          )}

          {/* Refresh Button */}
          {onRefresh && (
            <button
              onClick={onRefresh}
              disabled={loading}
              className="flex items-center gap-1.5 px-3 py-1.5 sm:px-4 sm:py-2 text-xs sm:text-sm font-medium rounded-full bg-primary/10 text-primary hover:bg-primary/20 transition-all hover:scale-105 active:scale-95 disabled:opacity-50 disabled:hover:scale-100"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
              <span className="hidden sm:inline">새로고침</span>
            </button>
          )}
        </div>
      </div>
    </header>
  )
}
