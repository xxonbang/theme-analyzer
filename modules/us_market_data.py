"""미국 시장 데이터 + 심리지표 + 테마 모멘텀 모듈"""
import requests
from datetime import datetime
from typing import Dict, List, Optional

from modules.utils import KST


def fetch_us_market_data() -> Optional[Dict]:
    """yfinance로 S&P500, NASDAQ, 섹터 ETF 전일 대비 등락률 수집"""
    try:
        import yfinance as yf

        tickers = {
            "S&P500": "^GSPC",
            "NASDAQ": "^IXIC",
            "반도체(SOXX)": "SOXX",
            "에너지(XLE)": "XLE",
            "금융(XLF)": "XLF",
            "기술(XLK)": "XLK",
            "헬스케어(XLV)": "XLV",
        }

        result = {}
        data = yf.download(
            list(tickers.values()), period="2d", progress=False, threads=True
        )

        if data.empty:
            return None

        close = data["Close"]
        for name, symbol in tickers.items():
            if symbol in close.columns and len(close[symbol].dropna()) >= 2:
                prices = close[symbol].dropna()
                prev, last = prices.iloc[-2], prices.iloc[-1]
                change_pct = ((last - prev) / prev) * 100
                result[name] = {
                    "price": round(float(last), 2),
                    "change_pct": round(float(change_pct), 2),
                }

        return result if result else None
    except Exception as e:
        print(f"  ⚠ US 시장 데이터 수집 실패: {e}")
        return None


def fetch_fear_greed_index() -> Optional[Dict]:
    """CNN Fear & Greed Index 조회"""
    try:
        today = datetime.now(KST).strftime("%Y-%m-%d")
        url = f"https://production.dataviz.cnn.io/index/fearandgreed/graphdata/{today}"
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        fg = data.get("fear_and_greed", {})
        score = fg.get("score")
        rating = fg.get("rating")
        if score is not None:
            return {"score": round(float(score), 2), "rating": rating or "N/A"}
        return None
    except Exception as e:
        print(f"  ⚠ Fear & Greed Index 수집 실패: {e}")
        return None


def calculate_theme_momentum(theme_history: List[Dict]) -> List[Dict]:
    """7일 히스토리에서 테마별 모멘텀 점수 계산

    점수 = frequency(0.4) + recency(0.3) + continuity(0.3)
    """
    if not theme_history:
        return []

    # 날짜순 정렬 (오래된 순)
    sorted_history = sorted(theme_history, key=lambda x: x.get("date", ""))
    total_days = len(sorted_history)

    # 테마별 등장 일자 인덱스 수집
    theme_days = {}  # theme_name -> [day_index, ...]
    for day_idx, entry in enumerate(sorted_history):
        for theme in entry.get("themes", []):
            name = theme.get("theme_name", "")
            if name:
                theme_days.setdefault(name, []).append(day_idx)

    result = []
    for name, days in theme_days.items():
        frequency = len(days) / total_days

        # recency: 마지막 등장 이후 경과일
        days_since_last = (total_days - 1) - max(days)
        recency = 1.0 / (days_since_last + 1)

        # continuity: 최장 연속 등장일 / 총 등장일
        max_streak = 1
        current_streak = 1
        sorted_days = sorted(days)
        for i in range(1, len(sorted_days)):
            if sorted_days[i] == sorted_days[i - 1] + 1:
                current_streak += 1
                max_streak = max(max_streak, current_streak)
            else:
                current_streak = 1
        continuity = max_streak / len(days) if days else 0

        score = frequency * 0.4 + recency * 0.3 + continuity * 0.3
        result.append({
            "theme_name": name,
            "score": round(score, 3),
            "frequency": len(days),
            "streak": max_streak,
        })

    result.sort(key=lambda x: x["score"], reverse=True)
    return result
