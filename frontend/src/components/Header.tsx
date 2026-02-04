import { useState } from "react"
import { BarChart3, RefreshCw, LayoutGrid, List, Calendar, Clock } from "lucide-react"
import { cn } from "@/lib/utils"

interface HeaderProps {
  timestamp?: string
  onRefresh?: () => void
  loading?: boolean
  compactMode?: boolean
  onToggleCompact?: () => void
}

export function Header({ timestamp, onRefresh, loading, compactMode, onToggleCompact }: HeaderProps) {
  const [showTooltip, setShowTooltip] = useState(false)
  const [ripple, setRipple] = useState<{ x: number; y: number; show: boolean }>({ x: 0, y: 0, show: false })

  // Ripple 효과 핸들러
  const handleRipple = (e: React.MouseEvent<HTMLButtonElement>) => {
    const rect = e.currentTarget.getBoundingClientRect()
    setRipple({
      x: e.clientX - rect.left,
      y: e.clientY - rect.top,
      show: true,
    })
    setTimeout(() => setRipple(prev => ({ ...prev, show: false })), 500)
  }

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
    return null
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
          {/* Timestamp Badge */}
          {parsed && (
            <div
              className="relative"
              onMouseEnter={() => setShowTooltip(true)}
              onMouseLeave={() => setShowTooltip(false)}
            >
              <div className="flex items-center gap-1.5 px-2.5 py-1.5 sm:px-3 sm:py-2 rounded-full bg-gradient-to-r from-muted/80 to-muted/50 border border-border/50 shadow-sm cursor-default">
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
                </span>
                <div className="flex items-center gap-1.5 sm:gap-2">
                  <div className="flex items-center gap-1">
                    <Calendar className="w-3 h-3 text-muted-foreground hidden sm:block" />
                    <span className="text-[10px] sm:text-xs font-medium">
                      <span className="hidden sm:inline">{parsed.fullDate}</span>
                      <span className="sm:hidden">{parsed.shortDate}</span>
                      <span className="text-muted-foreground ml-0.5">({parsed.weekday})</span>
                    </span>
                  </div>
                  <span className="w-px h-3 bg-border/70 hidden sm:block"></span>
                  <div className="flex items-center gap-1">
                    <Clock className="w-3 h-3 text-muted-foreground hidden sm:block" />
                    <span className="text-[10px] sm:text-xs font-semibold tabular-nums">{parsed.fullTime}</span>
                  </div>
                </div>
              </div>
              {showTooltip && relativeTime && (
                <div className="absolute top-full left-1/2 -translate-x-1/2 mt-2 px-2.5 py-1.5 bg-popover text-popover-foreground text-xs font-medium rounded-md shadow-lg border border-border whitespace-nowrap z-50 animate-in fade-in-0 zoom-in-95 duration-200">
                  <span className="text-green-500">●</span> {relativeTime} 업데이트
                  <div className="absolute -top-1 left-1/2 -translate-x-1/2 w-2 h-2 bg-popover border-l border-t border-border rotate-45"></div>
                </div>
              )}
            </div>
          )}

          {/* Compact Mode Toggle - Modern Animated Button */}
          {onToggleCompact && (
            <button
              onClick={(e) => {
                handleRipple(e)
                onToggleCompact()
              }}
              className={cn(
                "relative overflow-hidden group",
                "flex items-center justify-center w-9 h-9 sm:w-10 sm:h-10",
                "rounded-xl",
                "bg-gradient-to-br from-secondary via-secondary to-secondary/80",
                "border border-border/50",
                "shadow-sm hover:shadow-md hover:shadow-primary/10",
                "transition-all duration-300 ease-out",
                "hover:scale-110 active:scale-95",
                "hover:border-primary/30",
                "focus:outline-none focus:ring-2 focus:ring-primary/30 focus:ring-offset-2 focus:ring-offset-background"
              )}
              title={compactMode ? "상세 보기" : "간단 보기"}
            >
              {/* Glow effect on hover */}
              <div className="absolute inset-0 rounded-xl bg-gradient-to-br from-primary/20 via-primary/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />

              {/* Shimmer effect */}
              <div className="absolute inset-0 -translate-x-full group-hover:translate-x-full transition-transform duration-700 ease-out bg-gradient-to-r from-transparent via-white/10 to-transparent" />

              {/* Icon with rotation animation */}
              <div className={cn(
                "relative z-10 transition-all duration-300",
                "group-hover:rotate-12 group-active:rotate-0"
              )}>
                {compactMode ? (
                  <LayoutGrid className="w-4 h-4 sm:w-5 sm:h-5 transition-transform duration-300 group-hover:scale-110" />
                ) : (
                  <List className="w-4 h-4 sm:w-5 sm:h-5 transition-transform duration-300 group-hover:scale-110" />
                )}
              </div>

              {/* Ripple effect */}
              {ripple.show && (
                <span
                  className="absolute rounded-full bg-primary/30 animate-ripple"
                  style={{
                    left: ripple.x,
                    top: ripple.y,
                    width: '4px',
                    height: '4px',
                    transform: 'translate(-50%, -50%)',
                  }}
                />
              )}
            </button>
          )}

          {/* Refresh Button - Modern Animated Button */}
          {onRefresh && (
            <button
              onClick={(e) => {
                if (!loading) {
                  handleRipple(e)
                  onRefresh()
                }
              }}
              disabled={loading}
              className={cn(
                "relative overflow-hidden group",
                "flex items-center gap-1.5 px-3 py-2 sm:px-4 sm:py-2.5",
                "rounded-xl",
                "font-medium text-xs sm:text-sm",
                "bg-gradient-to-br from-primary/10 via-primary/5 to-primary/10",
                "text-primary",
                "border border-primary/20",
                "shadow-sm",
                "transition-all duration-300 ease-out",
                "hover:shadow-lg hover:shadow-primary/20",
                "hover:scale-105 hover:border-primary/40",
                "hover:from-primary/20 hover:via-primary/10 hover:to-primary/20",
                "active:scale-95",
                "focus:outline-none focus:ring-2 focus:ring-primary/30 focus:ring-offset-2 focus:ring-offset-background",
                "disabled:opacity-60 disabled:cursor-not-allowed disabled:hover:scale-100 disabled:hover:shadow-sm"
              )}
            >
              {/* Animated glow border */}
              <div className={cn(
                "absolute inset-0 rounded-xl",
                "bg-gradient-to-r from-primary/0 via-primary/30 to-primary/0",
                "opacity-0 group-hover:opacity-100",
                "transition-opacity duration-300",
                !loading && "group-hover:animate-pulse"
              )} />

              {/* Shimmer sweep effect */}
              <div className={cn(
                "absolute inset-0 -translate-x-full transition-transform duration-700 ease-out",
                "bg-gradient-to-r from-transparent via-white/20 to-transparent",
                !loading && "group-hover:translate-x-full"
              )} />

              {/* Icon */}
              <RefreshCw className={cn(
                "relative z-10 w-3.5 h-3.5 sm:w-4 sm:h-4",
                "transition-transform duration-500",
                loading ? "animate-spin" : "group-hover:rotate-180"
              )} />

              {/* Text with subtle animation */}
              <span className={cn(
                "relative z-10 hidden sm:inline",
                "transition-all duration-300",
                "group-hover:tracking-wide"
              )}>
                {loading ? "갱신 중..." : "새로고침"}
              </span>

              {/* Ripple effect */}
              {ripple.show && !loading && (
                <span
                  className="absolute rounded-full bg-primary/40 animate-ripple"
                  style={{
                    left: ripple.x,
                    top: ripple.y,
                    width: '4px',
                    height: '4px',
                    transform: 'translate(-50%, -50%)',
                  }}
                />
              )}
            </button>
          )}
        </div>
      </div>

      {/* Custom styles for ripple animation */}
      <style>{`
        @keyframes ripple {
          0% {
            transform: translate(-50%, -50%) scale(0);
            opacity: 1;
          }
          100% {
            transform: translate(-50%, -50%) scale(40);
            opacity: 0;
          }
        }
        .animate-ripple {
          animation: ripple 0.5s ease-out forwards;
        }
      `}</style>
    </header>
  )
}
