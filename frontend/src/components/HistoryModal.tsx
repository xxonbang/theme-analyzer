import { useEffect, useRef, useState } from "react"
import { X, Clock, Loader2, AlertCircle, ArrowRight, Database } from "lucide-react"
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
  const [isClosing, setIsClosing] = useState(false)

  // 닫기 애니메이션 처리
  const handleClose = () => {
    setIsClosing(true)
    setTimeout(() => {
      setIsClosing(false)
      onClose()
    }, 200)
  }

  // ESC 키로 닫기
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isOpen) {
        handleClose()
      }
    }
    window.addEventListener("keydown", handleKeyDown)
    return () => window.removeEventListener("keydown", handleKeyDown)
  }, [isOpen])

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
      handleClose()
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

  // 날짜 포맷 (2026-02-04 -> 02.04)
  const formatDateShort = (dateStr: string) => {
    const parts = dateStr.split("-")
    return `${parts[1]}.${parts[2]}`
  }

  // 상대적 날짜 표시
  const getRelativeDate = (dateStr: string) => {
    const today = new Date()
    const [year, month, day] = dateStr.split("-")
    const targetDate = new Date(parseInt(year), parseInt(month) - 1, parseInt(day))
    const diffTime = today.getTime() - targetDate.getTime()
    const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24))

    if (diffDays === 0) return "오늘"
    if (diffDays === 1) return "어제"
    if (diffDays < 7) return `${diffDays}일 전`
    return null
  }

  return (
    <div
      className={cn(
        "fixed inset-0 z-50 flex items-center justify-center p-4",
        "transition-all duration-200",
        isClosing ? "opacity-0" : "opacity-100"
      )}
      onClick={handleBackdropClick}
    >
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" />

      {/* Modal Container */}
      <div
        ref={modalRef}
        className={cn(
          "relative w-full max-w-sm max-h-[80vh] flex flex-col",
          "rounded-xl overflow-hidden",
          "bg-card",
          "border border-border",
          "shadow-xl",
          // Animation
          "transition-all duration-200 ease-out",
          isClosing
            ? "scale-95 opacity-0"
            : "scale-100 opacity-100 animate-in zoom-in-95"
        )}
      >
        {/* Header */}
        <div className="relative flex items-center justify-between px-5 py-4 border-b border-border/50">
          <div className="flex items-center gap-3">
            <div className="flex items-center justify-center w-9 h-9 rounded-lg bg-primary/10">
              <Clock className="w-4 h-4 text-primary" />
            </div>
            <div>
              <h2 className="font-semibold text-base">히스토리</h2>
              <p className="text-[11px] text-muted-foreground">과거 분석 결과</p>
            </div>
          </div>

          {/* Close button */}
          <button
            onClick={handleClose}
            className="p-1.5 rounded-md hover:bg-muted transition-colors"
          >
            <X className="w-4 h-4 text-muted-foreground" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-4 py-3 custom-scrollbar">
          {/* Loading State */}
          {loading && (
            <div className="flex flex-col items-center justify-center py-16">
              <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
              <p className="mt-3 text-xs text-muted-foreground">불러오는 중...</p>
            </div>
          )}

          {/* Error State */}
          {error && (
            <div className="flex flex-col items-center justify-center py-16">
              <AlertCircle className="w-6 h-6 text-destructive/70" />
              <p className="mt-3 text-xs text-destructive/70">{error}</p>
            </div>
          )}

          {/* Empty State - Minimal Modern Design */}
          {!loading && !error && groupedHistory.length === 0 && (
            <div className="flex flex-col items-center justify-center py-16">
              {/* Minimal icon */}
              <div className="relative mb-8">
                <div className="w-16 h-16 rounded-2xl bg-muted/50 border border-border/80 flex items-center justify-center">
                  <Database className="w-7 h-7 text-muted-foreground/40" />
                </div>
              </div>

              {/* Text content */}
              <div className="text-center space-y-3">
                <h3 className="text-sm font-medium text-foreground">
                  저장된 히스토리가 없습니다
                </h3>
                <p className="text-xs text-muted-foreground/70 max-w-[200px] leading-relaxed">
                  분석 실행 후 기록이 저장됩니다
                </p>
              </div>

              {/* Schedule info */}
              <div className="mt-8 text-xs text-muted-foreground/60">
                매일 09:30, 21:00 자동 업데이트
              </div>
            </div>
          )}

          {/* History List */}
          {!loading && !error && groupedHistory.length > 0 && (
            <div className="space-y-0.5">
              {groupedHistory.flatMap((group) =>
                group.entries.map((entry) => (
                  <button
                    key={entry.filename}
                    onClick={() => onSelect(entry)}
                    className={cn(
                      "group w-full flex items-center gap-2 px-2 py-2 rounded-md",
                      "text-left",
                      "hover:bg-muted/50",
                      "transition-colors duration-150"
                    )}
                  >
                    <span className="text-xs text-muted-foreground tabular-nums">
                      {formatDateShort(entry.date)} ({getWeekday(entry.date)})
                    </span>
                    <span className="font-medium text-xs tabular-nums">
                      {entry.time}
                    </span>
                    {getRelativeDate(entry.date) && (
                      <span className="text-[10px] text-primary/60">
                        {getRelativeDate(entry.date)}
                      </span>
                    )}
                    <ArrowRight className="w-3 h-3 text-muted-foreground/30 ml-auto opacity-0 group-hover:opacity-100 transition-opacity" />
                  </button>
                ))
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-5 py-3 border-t border-border/50 bg-muted/20">
          <p className="text-[11px] text-muted-foreground text-center">
            최근 30일간의 기록
          </p>
        </div>
      </div>

      {/* Custom scrollbar styles */}
      <style>{`
        .custom-scrollbar::-webkit-scrollbar {
          width: 6px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: transparent;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background: hsl(var(--muted-foreground) / 0.2);
          border-radius: 3px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover {
          background: hsl(var(--muted-foreground) / 0.3);
        }
      `}</style>
    </div>
  )
}
