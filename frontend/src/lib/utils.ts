import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatPrice(price: number): string {
  return price.toLocaleString("ko-KR")
}

export function formatVolume(volume: number): string {
  if (volume >= 1_000_000) {
    return `${(volume / 1_000_000).toFixed(1)}M`
  } else if (volume >= 1_000) {
    return `${Math.floor(volume / 1_000)}K`
  }
  return volume.toString()
}

export function formatChangeRate(rate: number): string {
  const sign = rate > 0 ? "+" : ""
  return `${sign}${rate.toFixed(2)}%`
}

export function getWeekday(dateStr: string): string {
  const weekdays = ["일", "월", "화", "수", "목", "금", "토"]
  const [year, month, day] = dateStr.split("-")
  const date = new Date(parseInt(year), parseInt(month) - 1, parseInt(day))
  return weekdays[date.getDay()]
}

export function formatTradingValue(value: number): string {
  if (value >= 1_000_000_000_000) {
    return `${(value / 1_000_000_000_000).toFixed(1)}조`
  } else if (value >= 100_000_000) {
    return `${Math.floor(value / 100_000_000)}억`
  } else if (value >= 10_000) {
    return `${Math.floor(value / 10_000)}만`
  }
  return value.toLocaleString("ko-KR")
}

export function formatNetBuy(qty: number): string {
  const sign = qty > 0 ? "+" : ""
  const abs = Math.abs(qty)
  if (abs >= 10000) {
    return `${sign}${Math.round(qty / 10000)}만`
  }
  return `${sign}${qty.toLocaleString("ko-KR")}`
}

export function getNetBuyColor(qty: number): string {
  if (qty > 0) return "text-red-500"
  if (qty < 0) return "text-blue-500"
  return "text-muted-foreground"
}

export function getChangeBgColor(rate: number): string {
  if (rate >= 10) return "bg-red-100 text-red-700"
  if (rate >= 5) return "bg-red-50 text-red-600"
  if (rate > 0) return "bg-red-50/70 text-red-500"
  if (rate <= -10) return "bg-blue-100 text-blue-700"
  if (rate <= -5) return "bg-blue-50 text-blue-600"
  if (rate < 0) return "bg-blue-50/70 text-blue-500"
  return "bg-muted text-muted-foreground"
}
