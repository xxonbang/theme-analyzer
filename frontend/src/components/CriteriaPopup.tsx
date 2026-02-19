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
    return typeof c !== "boolean" && c?.met
  })
  const unmetItems = CRITERIA_CONFIG.filter(({ key }) => {
    const c = criteria[key as keyof StockCriteria]
    return typeof c !== "boolean" && !c?.met && !c?.warning
  })

  return (
    <div className="absolute left-0 top-full mt-1 z-50 w-64 sm:w-72 bg-popover text-popover-foreground rounded-lg shadow-lg border border-border p-2.5 max-h-80 overflow-y-auto">
      <div className="flex items-center justify-between mb-1.5">
        <span className="text-xs font-semibold">{stockName} 기준 평가</span>
        <button
          onClick={onClose}
          className="text-muted-foreground hover:text-foreground"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      </div>
      {metItems.length > 0 && (
        <div className="space-y-1.5">
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
      {unmetItems.length > 0 && (
        <>
          <div className="flex items-center gap-1.5 mt-2.5 mb-1.5">
            <div className="flex-1 border-t border-border/50" />
            <span className="text-[9px] text-muted-foreground/60 shrink-0">미충족</span>
            <div className="flex-1 border-t border-border/50" />
          </div>
          <div className="space-y-1.5 opacity-60">
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
  )
}
