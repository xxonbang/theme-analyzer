import { useState, useEffect } from "react"
import { Header } from "@/components/Header"
import { ExchangeRate } from "@/components/ExchangeRate"
import { StockList } from "@/components/StockList"
import { HistoryModal } from "@/components/HistoryModal"
import { useStockData } from "@/hooks/useStockData"
import { useHistoryData } from "@/hooks/useHistoryData"
import { Loader2, ArrowLeft, Calendar, Clock } from "lucide-react"
import { cn } from "@/lib/utils"
import type { HistoryEntry } from "@/types/history"

// 로컬 스토리지 키
const COMPACT_MODE_KEY = "stock-dashboard-compact-mode"

function App() {
  const { data: currentData, loading, error, refetch } = useStockData()
  const {
    groupedHistory,
    selectedData: historyData,
    selectedEntry,
    loading: historyLoading,
    error: historyError,
    fetchIndex,
    fetchHistoryData,
    clearSelection,
  } = useHistoryData()

  // 히스토리 모달 상태
  const [showHistoryModal, setShowHistoryModal] = useState(false)

  // 컴팩트 모드 상태 (로컬 스토리지에서 복원)
  const [compactMode, setCompactMode] = useState(() => {
    const saved = localStorage.getItem(COMPACT_MODE_KEY)
    return saved === "true"
  })

  // 컴팩트 모드 변경 시 로컬 스토리지에 저장
  useEffect(() => {
    localStorage.setItem(COMPACT_MODE_KEY, String(compactMode))
  }, [compactMode])

  const toggleCompactMode = () => {
    setCompactMode((prev) => !prev)
  }

  // 현재 데이터 or 히스토리 데이터 표시
  const displayData = historyData || currentData
  const isViewingHistory = !!historyData

  // 히스토리 버튼 클릭 핸들러
  const handleHistoryClick = async () => {
    await fetchIndex()
    setShowHistoryModal(true)
  }

  // 히스토리 항목 선택 핸들러
  const handleHistorySelect = async (entry: HistoryEntry) => {
    await fetchHistoryData(entry)
    setShowHistoryModal(false)
  }

  // 실시간 데이터로 돌아가기
  const handleBackToLive = () => {
    clearSelection()
  }

  if (loading && !currentData) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="w-8 h-8 animate-spin text-primary" />
          <p className="text-muted-foreground text-sm">데이터를 불러오는 중...</p>
        </div>
      </div>
    )
  }

  // 요일 계산
  const getWeekday = (dateStr: string) => {
    const weekdays = ["일", "월", "화", "수", "목", "금", "토"]
    const [year, month, day] = dateStr.split("-")
    const date = new Date(parseInt(year), parseInt(month) - 1, parseInt(day))
    return weekdays[date.getDay()]
  }

  return (
    <div className="min-h-screen bg-background">
      <Header
        timestamp={displayData?.timestamp}
        onRefresh={refetch}
        loading={loading}
        compactMode={compactMode}
        onToggleCompact={toggleCompactMode}
        onHistoryClick={handleHistoryClick}
        isViewingHistory={isViewingHistory}
      />

      {/* 히스토리 보기 중 배너 */}
      {isViewingHistory && selectedEntry && (
        <div className="sticky top-14 sm:top-16 z-40 bg-muted/80 border-b border-border backdrop-blur-sm">
          <div className="container px-3 sm:px-4 py-2 sm:py-3 flex items-center justify-between">
            <div className="flex items-center gap-2 sm:gap-3">
              <div className="flex items-center gap-1.5 text-muted-foreground">
                <Calendar className="w-4 h-4" />
                <span className="text-xs sm:text-sm font-medium">
                  {selectedEntry.date.replace(/-/g, ".")} ({getWeekday(selectedEntry.date)})
                </span>
              </div>
              <div className="flex items-center gap-1.5 text-muted-foreground">
                <Clock className="w-4 h-4" />
                <span className="text-xs sm:text-sm font-medium">{selectedEntry.time}</span>
              </div>
              <span className="text-xs text-muted-foreground/70 hidden sm:inline">
                과거 데이터
              </span>
            </div>
            <button
              onClick={handleBackToLive}
              className={cn(
                "flex items-center gap-1.5 px-3 py-1.5 rounded-md",
                "text-xs sm:text-sm font-medium",
                "bg-primary/10 hover:bg-primary/20",
                "text-primary",
                "transition-colors duration-150"
              )}
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">최신으로 돌아가기</span>
              <span className="sm:hidden">돌아가기</span>
            </button>
          </div>
        </div>
      )}

      <main className="container px-3 sm:px-4 py-4 sm:py-6">
        {error && !isViewingHistory && (
          <div className="mb-4 sm:mb-6 p-3 sm:p-4 rounded-lg bg-warning/10 border border-warning/20 text-warning">
            <p className="text-xs sm:text-sm">{error} (데모 데이터를 표시합니다)</p>
          </div>
        )}

        {/* Exchange Rate - Top section */}
        {displayData?.exchange && <ExchangeRate exchange={displayData.exchange} />}

        {/* Stock Lists - Full width with 2-column cards inside */}
        <div className="space-y-4 sm:space-y-6">
          {/* Rising Stocks */}
          {displayData && (
            <StockList
              title="거래량 + 상승률 TOP10"
              kospiStocks={displayData.rising.kospi}
              kosdaqStocks={displayData.rising.kosdaq}
              history={displayData.history}
              news={displayData.news}
              type="rising"
              compactMode={compactMode}
            />
          )}

          {/* Falling Stocks */}
          {displayData && (
            <StockList
              title="거래량 + 하락률 TOP10"
              kospiStocks={displayData.falling.kospi}
              kosdaqStocks={displayData.falling.kosdaq}
              history={displayData.history}
              news={displayData.news}
              type="falling"
              compactMode={compactMode}
            />
          )}
        </div>

        {/* Footer */}
        <footer className="mt-8 sm:mt-12 pt-4 sm:pt-6 border-t text-center text-xs sm:text-sm text-muted-foreground">
          <p>KIS API + Naver News API 기반 자동 분석</p>
          <p className="mt-1">
            매일 09:30, 21:00 KST 업데이트
          </p>
        </footer>
      </main>

      {/* History Modal */}
      <HistoryModal
        isOpen={showHistoryModal}
        onClose={() => setShowHistoryModal(false)}
        groupedHistory={groupedHistory}
        onSelect={handleHistorySelect}
        loading={historyLoading}
        error={historyError}
      />
    </div>
  )
}

export default App
