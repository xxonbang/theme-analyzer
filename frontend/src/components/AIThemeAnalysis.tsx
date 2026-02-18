import { useState } from "react"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Sparkles, ChevronDown, ChevronUp, ExternalLink } from "lucide-react"
import { cn } from "@/lib/utils"
import type { ThemeAnalysis, MarketTheme, StockCriteria } from "@/types/stock"

/** 대장주 칩용 기준 도트 색상 (다른 컴포넌트와 동일 체계) */
const LEADER_CRITERIA = [
  { key: "high_breakout", dot: "bg-red-500" },
  { key: "momentum_history", dot: "bg-orange-500" },
  { key: "resistance_breakout", dot: "bg-yellow-400" },
  { key: "ma_alignment", dot: "bg-green-500" },
  { key: "supply_demand", dot: "bg-blue-500" },
  { key: "program_trading", dot: "bg-lime-400" },
  { key: "top30_trading_value", dot: "bg-pink-500" },
] as const

interface AIThemeAnalysisProps {
  themeAnalysis: ThemeAnalysis
  showRefresh?: boolean
  criteriaData?: Record<string, StockCriteria>
  isAdmin?: boolean
}

function ThemeCard({ theme, index, criteriaData, isAdmin }: { theme: MarketTheme; index: number; criteriaData?: Record<string, StockCriteria>; isAdmin?: boolean }) {
  const [expanded, setExpanded] = useState(false)
  const showCriteria = isAdmin && criteriaData

  return (
    <div className="border rounded-lg p-3 sm:p-4 space-y-2.5">
      {/* 테마 헤더 */}
      <div className="flex items-start gap-2">
        <Badge variant="secondary" className="shrink-0 text-[10px] sm:text-xs">
          테마 {index + 1}
        </Badge>
        <div className="min-w-0">
          <h4 className="font-semibold text-sm sm:text-base leading-tight">{theme.theme_name}</h4>
          <p className="text-xs sm:text-sm text-muted-foreground mt-0.5 leading-relaxed">
            {theme.theme_description}
          </p>
        </div>
      </div>

      <hr className="border-border/50" />

      {/* 대장주 칩 */}
      <div className="flex flex-wrap items-center gap-1.5 sm:gap-2">
        <Badge variant="secondary" className="shrink-0 text-[10px] sm:text-xs">대장주</Badge>
        {theme.leader_stocks.map((stock) => {
          const criteria = showCriteria ? criteriaData[stock.code] : undefined
          const allMet = criteria?.all_met
          const metDots = criteria ? LEADER_CRITERIA.filter(({ key }) => {
            const c = criteria[key as keyof StockCriteria]
            return typeof c !== "boolean" && c?.met
          }) : []
          const hasDots = metDots.length > 0

          return (
            <a
              key={stock.code}
              href={`https://m.stock.naver.com/domestic/stock/${stock.code}/total`}
              target="_blank"
              rel="noopener noreferrer"
              className={cn(
                "inline-flex items-center gap-1 px-2 py-1 rounded-md",
                "text-xs sm:text-sm font-medium",
                "transition-all duration-150",
                allMet
                  ? "bg-yellow-400/15 hover:bg-yellow-400/25 text-yellow-700 ring-1 ring-yellow-400/60 animate-[shimmer_3s_ease-in-out_infinite]"
                  : "bg-primary/10 hover:bg-primary/20 text-primary"
              )}
            >
              {hasDots && (
                <span className="inline-flex items-center gap-px mr-0.5">
                  {metDots.map(({ key, dot }) => (
                    <span key={key} className={cn("w-1.5 h-1.5 rounded-full", dot)} />
                  ))}
                </span>
              )}
              {stock.name}
              <ExternalLink className="w-3 h-3 opacity-50" />
            </a>
          )
        })}
      </div>

      <hr className="border-border/50" />

      {/* 뉴스 근거 토글 */}
      <button
        onClick={() => setExpanded(!expanded)}
        className={cn(
          "flex items-center gap-1 text-xs text-muted-foreground",
          "hover:text-foreground transition-colors duration-150"
        )}
      >
        {expanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
        {expanded ? "뉴스 근거 접기" : "뉴스 근거 보기"}
      </button>

      {/* 뉴스 근거 상세 */}
      {expanded && (
        <div className="space-y-3">
          {theme.leader_stocks.map((stock) => (
            <div key={stock.code} className="pt-2 first:pt-0">
              <div className="mb-1.5">
                <span className="inline-flex items-center px-1.5 py-0.5 rounded bg-foreground/5 font-semibold text-xs sm:text-sm">
                  {stock.name}
                </span>
              </div>
              <p className="text-[11px] sm:text-xs text-muted-foreground leading-relaxed mb-2 pl-0.5">
                {stock.reason}
              </p>
              {stock.news_evidence.length > 0 && (
                <ul className="space-y-1 pl-0.5">
                  {stock.news_evidence.map((news, i) => (
                    <li key={i} className="flex items-start gap-1.5 text-[11px] sm:text-xs">
                      <span className="text-muted-foreground/50 shrink-0 mt-px">{'•'}</span>
                      <a
                        href={news.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-muted-foreground hover:text-foreground hover:underline transition-colors break-words"
                      >
                        {news.title}
                      </a>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export function AIThemeAnalysis({ themeAnalysis, criteriaData, isAdmin }: AIThemeAnalysisProps) {
  const [collapsed, setCollapsed] = useState(false)

  if (!themeAnalysis?.themes?.length) {
    return null
  }

  const themeCount = themeAnalysis.themes.length

  return (
    <Card className="mb-4 sm:mb-6 overflow-hidden shadow-sm">
      <CardContent className="p-3 sm:p-4 space-y-3">
        {/* 헤더 (클릭으로 전체 토글) */}
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="flex items-center justify-between w-full text-left"
        >
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 sm:w-5 sm:h-5 text-amber-500" />
            <span className="font-semibold text-sm sm:text-base">AI 테마 분석</span>
            <span className="text-[10px] sm:text-xs text-muted-foreground">
              ({themeAnalysis.analysis_date} {themeAnalysis.analyzed_at.split(" ")[1]} 분석)
            </span>
          </div>
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <Badge variant="secondary" className="text-[10px] sm:text-xs">{themeCount}개 테마</Badge>
            {collapsed ? <ChevronDown className="w-4 h-4" /> : <ChevronUp className="w-4 h-4" />}
          </div>
        </button>

        {/* 시장 요약 (항상 표시) */}
        <p className="text-xs sm:text-sm text-muted-foreground bg-muted/50 rounded-md px-3 py-2 leading-relaxed">
          {themeAnalysis.market_summary}
        </p>

        {/* 테마 카드 (접기/펼치기) */}
        {!collapsed && (
          <div className="space-y-2.5">
            {themeAnalysis.themes.map((theme, index) => (
              <ThemeCard key={index} theme={theme} index={index} criteriaData={criteriaData} isAdmin={isAdmin} />
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
