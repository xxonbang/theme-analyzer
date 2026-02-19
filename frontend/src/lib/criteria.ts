/** 기준별 색상 및 라벨 정의 (우선순위 순) — 단일 정의, 전체 컴포넌트에서 공유 */
export const CRITERIA_CONFIG = [
  { key: "high_breakout", dot: "bg-red-500", badge: "bg-red-100 text-red-700", label: "전고점 돌파", shortLabel: "전고점" },
  { key: "supply_demand", dot: "bg-blue-500", badge: "bg-blue-100 text-blue-700", label: "외국인/기관 수급", shortLabel: "수급" },
  { key: "program_trading", dot: "bg-violet-500", badge: "bg-violet-100 text-violet-700", label: "프로그램 매매", shortLabel: "프로그램" },
  { key: "momentum_history", dot: "bg-orange-500", badge: "bg-orange-100 text-orange-700", label: "끼 보유", shortLabel: "끼" },
  { key: "resistance_breakout", dot: "bg-yellow-400", badge: "bg-yellow-100 text-yellow-700", label: "저항선 돌파", shortLabel: "저항선" },
  { key: "ma_alignment", dot: "bg-teal-500", badge: "bg-teal-100 text-teal-700", label: "정배열", shortLabel: "정배열" },
  { key: "top30_trading_value", dot: "bg-fuchsia-500", badge: "bg-fuchsia-100 text-fuchsia-700", label: "거래대금 TOP30", shortLabel: "TOP30" },
  { key: "market_cap", dot: "bg-emerald-500", badge: "bg-emerald-100 text-emerald-700", label: "시가총액", shortLabel: "시총" },
  { key: "short_selling", dot: "bg-red-600", badge: "bg-red-100 text-red-800", label: "공매도 경고", shortLabel: "공매도" },
] as const
