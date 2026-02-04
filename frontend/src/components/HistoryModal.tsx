import { useEffect, useRef } from "react"
import { X, Calendar, Clock, Loader2, History, AlertCircle } from "lucide-react"
import { cn } from "@/lib/utils"
import type { GroupedHistory, HistoryEntry } from "@/types/history"

interface HistoryModalProps {
  isOpen: boolean
  onClose: () => void
  groupedHistory: GroupedHistory[]
  onSelect: (entry: HistoryEntry) => void
  loading: boolean
  error: string | null
}

export function HistoryModal({
  isOpen,
  onClose,
  groupedHistory,
  onSelect,
  loading,
  error,
}: HistoryModalProps) {
  const modalRef = useRef<HTMLDivElement>(null)

  // ESC 키로 닫기
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isOpen) {
        onClose()
      }
    }
    window.addEventListener("keydown", handleKeyDown)
    return () => window.removeEventListener("keydown", handleKeyDown)
  }, [isOpen, onClose])

  // 모달 열릴 때 스크롤 방지
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = "hidden"
    } else {
      document.body.style.overflow = ""
    }
    return () => {
      document.body.style.overflow = ""
    }
  }, [isOpen])

  // 배경 클릭으로 닫기
  const handleBackdropClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
      onClose()
    }
  }

  if (!isOpen) return null

  // 요일 계산
  const getWeekday = (dateStr: string) => {
    const weekdays = ["일", "월", "화", "수", "목", "금", "토"]
    const [year, month, day] = dateStr.split("-")
    const date = new Date(parseInt(year), parseInt(month) - 1, parseInt(day))
    return weekdays[date.getDay()]
  }

  // 날짜 포맷 (2026-02-04 -> 2026.02.04)
  const formatDate = (dateStr: string) => {
    return dateStr.replace(/-/g, ".")
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm animate-in fade-in duration-200"
      onClick={handleBackdropClick}
    >
      <div
        ref={modalRef}
        className="relative w-full max-w-md mx-4 max-h-[80vh] bg-card border border-border rounded-xl shadow-2xl animate-in zoom-in-95 duration-200 flex flex-col"
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-border">
          <div className="flex items-center gap-2">
            <History className="w-5 h-5 text-primary" />
            <h2 className="font-semibold text-lg">히스토리</h2>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-muted transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4">
          {loading && (
            <div className="flex flex-col items-center justify-center py-12">
              <Loader2 className="w-8 h-8 animate-spin text-primary mb-3" />
              <p className="text-sm text-muted-foreground">불러오는 중...</p>
            </div>
          )}

          {error && (
            <div className="flex flex-col items-center justify-center py-12">
              <AlertCircle className="w-8 h-8 text-destructive mb-3" />
              <p className="text-sm text-destructive">{error}</p>
            </div>
          )}

          {!loading && !error && groupedHistory.length === 0 && (
            <div className="flex flex-col items-center justify-center py-12">
              <History className="w-12 h-12 text-muted-foreground/50 mb-3" />
              <p className="text-sm text-muted-foreground">저장된 히스토리가 없습니다</p>
              <p className="text-xs text-muted-foreground/70 mt-1">
                분석 실행 후 히스토리가 저장됩니다
              </p>
            </div>
          )}

          {!loading && !error && groupedHistory.length > 0 && (
            <div className="space-y-4">
              {groupedHistory.map((group) => (
                <div key={group.date}>
                  {/* 날짜 헤더 */}
                  <div className="flex items-center gap-2 mb-2">
                    <Calendar className="w-4 h-4 text-muted-foreground" />
                    <span className="text-sm font-medium">
                      {formatDate(group.date)}
                      <span className="text-muted-foreground ml-1">
                        ({getWeekday(group.date)})
                      </span>
                    </span>
                  </div>

                  {/* 시간 목록 */}
                  <div className="ml-6 space-y-1">
                    {group.entries.map((entry) => (
                      <button
                        key={entry.filename}
                        onClick={() => onSelect(entry)}
                        className={cn(
                          "w-full flex items-center gap-2 px-3 py-2 rounded-lg",
                          "text-left text-sm",
                          "bg-muted/50 hover:bg-primary/10 hover:text-primary",
                          "border border-transparent hover:border-primary/20",
                          "transition-all duration-200"
                        )}
                      >
                        <Clock className="w-4 h-4 text-muted-foreground" />
                        <span className="font-medium tabular-nums">{entry.time}</span>
                        <span className="text-xs text-muted-foreground ml-auto">
                          {entry.time === "09:30" ? "장 시작" : entry.time === "21:00" ? "장 마감" : ""}
                        </span>
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-4 py-3 border-t border-border bg-muted/30">
          <p className="text-xs text-muted-foreground text-center">
            최근 30일간의 분석 결과를 조회할 수 있습니다
          </p>
        </div>
      </div>
    </div>
  )
}
