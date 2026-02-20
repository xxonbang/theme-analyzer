import { useEffect } from "react"
import { createPortal } from "react-dom"
import { X } from "lucide-react"
import { cn } from "@/lib/utils"
import { CRITERIA_CONFIG } from "@/lib/criteria"
import type { StockCriteria } from "@/types/stock"

interface CriteriaPopupProps {
  stockName: string
  criteria: StockCriteria
  onClose: () => void
}

export function CriteriaPopup({ stockName, criteria, onClose }: CriteriaPopupProps) {
  const metItems = CRITERIA_CONFIG.filter(({ key }) => {
    const c = criteria[key as keyof StockCriteria]
    return typeof c !== "boolean" && c?.met && !c?.warning
  })
  const warningItems = CRITERIA_CONFIG.filter(({ key }) => {
    const c = criteria[key as keyof StockCriteria]
    return typeof c !== "boolean" && c?.met && c?.warning
  })
  const unmetItems = CRITERIA_CONFIG.filter(({ key }) => {
    const c = criteria[key as keyof StockCriteria]
    return typeof c !== "boolean" && !c?.met && !c?.warning
  })

  // 스크롤 잠금
  useEffect(() => {
    const scrollY = window.scrollY
    document.body.style.overflow = "hidden"
    document.body.style.position = "fixed"
    document.body.style.top = `-${scrollY}px`
    document.body.style.left = "0"
    document.body.style.right = "0"
    return () => {
      document.body.style.overflow = ""
      document.body.style.position = ""
      document.body.style.top = ""
      document.body.style.left = ""
      document.body.style.right = ""
      window.scrollTo(0, scrollY)
    }
  }, [])

  return createPortal(
    <div className="fixed inset-0 z-[45] flex items-end sm:items-center justify-center">
      {/* 백드롭 */}
      <div className="absolute inset-0 bg-black/25" onClick={onClose} />

      {/* 팝업 컨텐츠 */}
      <div className="relative w-full sm:w-80 sm:max-w-[90vw] max-h-[70vh] overflow-y-auto bg-popover text-popover-foreground rounded-t-xl sm:rounded-xl shadow-xl border border-border p-3 sm:p-4">
        {/* 모바일 드래그 핸들 */}
        <div className="sm:hidden flex justify-center mb-2">
          <div className="w-10 h-1 rounded-full bg-muted-foreground/30" />
        </div>

        {/* 헤더 */}
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-semibold">{stockName} 기준 평가</span>
          <button
            onClick={onClose}
            className="text-muted-foreground hover:text-foreground p-1 -m-1"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* 충족 기준 */}
        {metItems.length > 0 && (
          <div className="space-y-2">
            {metItems.map(({ key, dot, label }) => {
              const c = criteria[key as keyof StockCriteria]
              if (typeof c === "boolean") return null
              return (
                <div key={key}>
                  <div className="flex items-center gap-1.5">
                    <span className={cn("w-2 h-2 rounded-full shrink-0", dot)} />
                    <span className="text-[10px] font-semibold">{label}</span>
                  </div>
                  <p className="text-[9px] sm:text-[10px] text-muted-foreground leading-relaxed pl-3.5">{c?.reason || "근거 없음"}</p>
                </div>
              )
            })}
          </div>
        )}

        {/* 경고 섹션 */}
        {warningItems.length > 0 && (
          <>
            <div className="flex items-center gap-1.5 mt-3 mb-2">
              <div className="flex-1 border-t border-red-300" />
              <span className="text-[9px] text-red-500 font-medium shrink-0">경고</span>
              <div className="flex-1 border-t border-red-300" />
            </div>
            <div className="space-y-2">
              {warningItems.map(({ key, dot, label }) => {
                const c = criteria[key as keyof StockCriteria]
                if (typeof c === "boolean") return null
                const levelSuffix = c?.level ? ` (${c.level})` : ""
                return (
                  <div key={key}>
                    <div className="flex items-center gap-1.5">
                      <span className={cn("w-2 h-2 rounded-full shrink-0", dot)} />
                      <span className="text-[10px] font-semibold text-red-600">{label}{levelSuffix}</span>
                    </div>
                    <p className="text-[9px] sm:text-[10px] text-red-500/80 leading-relaxed pl-3.5">{c?.reason || "근거 없음"}</p>
                  </div>
                )
              })}
            </div>
          </>
        )}

        {/* 미충족 기준 */}
        {unmetItems.length > 0 && (
          <>
            <div className="flex items-center gap-1.5 mt-3 mb-2">
              <div className="flex-1 border-t border-border/50" />
              <span className="text-[9px] text-muted-foreground/60 shrink-0">미충족</span>
              <div className="flex-1 border-t border-border/50" />
            </div>
            <div className="space-y-2 opacity-60">
              {unmetItems.map(({ key, label }) => {
                const c = criteria[key as keyof StockCriteria]
                if (typeof c === "boolean") return null
                return (
                  <div key={key}>
                    <div className="flex items-center gap-1.5">
                      <span className="w-2 h-2 rounded-full shrink-0 bg-gray-300 dark:bg-gray-600" />
                      <span className="text-[10px] font-medium text-muted-foreground">{label}</span>
                    </div>
                    <p className="text-[9px] sm:text-[10px] text-muted-foreground/70 leading-relaxed pl-3.5">{c?.reason || ""}</p>
                  </div>
                )
              })}
            </div>
          </>
        )}
      </div>
    </div>,
    document.body
  )
}
