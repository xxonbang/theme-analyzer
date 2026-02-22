"""미국 시장 데이터 + 심리지표 + 경제 캘린더 + 테마 모멘텀 모듈"""
import os
import re
from typing import Dict, List, Optional


def _normalize_theme_name(name: str) -> str:
    """모멘텀/로테이션 비교용 테마명 정규화

    괄호 내용 제거, 특수문자→공백 통일, 양쪽 공백 제거.
    예: "AI/반도체(HBM)" → "AI 반도체"
    """
    name = re.sub(r'\([^)]*\)', '', name)
    name = re.sub(r'[/·・\-]', ' ', name)
    return re.sub(r'\s+', ' ', name).strip()


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
            "WTI유가": "CL=F",
            "금": "GC=F",
            "미국10Y국채금리": "^TNX",
            "달러인덱스": "DX-Y.NYB",
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


def fetch_vix_index() -> Optional[Dict]:
    """VIX(공포지수) 조회 — yfinance 사용

    VIX 수치별 시장 심리:
      0~15  안정(Low)  | 15~25 보통(Normal)
      25~35 불안(High) | 35+   공포(Extreme)
    """
    try:
        import yfinance as yf

        vix = yf.Ticker("^VIX")
        hist = vix.history(period="2d")
        if hist.empty or len(hist) < 1:
            return None

        current = float(hist["Close"].iloc[-1])
        # 심리 등급 판정
        if current < 15:
            rating = "안정 (Low Volatility)"
        elif current < 25:
            rating = "보통 (Normal)"
        elif current < 35:
            rating = "불안 (High Volatility)"
        else:
            rating = "공포 (Extreme Fear)"

        return {"score": round(current, 2), "rating": rating}
    except Exception as e:
        print(f"  ⚠ VIX 지수 수집 실패: {e}")
        return None


def fetch_global_market_news() -> Optional[List[Dict]]:
    """Finnhub Market News — 최신 글로벌 시장 뉴스 20건 수집

    Returns:
        [{"headline", "summary", "source", "datetime", "url"}]
        실패 시 None
    """
    api_key = os.getenv("FINNHUB_API_KEY")
    if not api_key:
        print("  ⚠ FINNHUB_API_KEY 미설정")
        return None

    try:
        import requests
        from datetime import datetime

        resp = requests.get(
            "https://finnhub.io/api/v1/news",
            params={"category": "general", "token": api_key},
            timeout=10,
        )
        resp.raise_for_status()
        news = resp.json()

        if not news:
            return None

        # 최신 20건만, 필요한 필드만 추출
        result = []
        for item in news[:20]:
            ts = item.get("datetime", 0)
            time_str = datetime.utcfromtimestamp(ts).strftime("%m/%d %H:%M") if ts else "N/A"
            result.append({
                "headline": item.get("headline", ""),
                "summary": item.get("summary", "")[:200],
                "source": item.get("source", ""),
                "time": time_str,
            })

        return result if result else None
    except Exception as e:
        print(f"  ⚠ Finnhub 글로벌 뉴스 수집 실패: {e}")
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

    # 테마별 등장 일자 인덱스 수집 (정규화된 이름으로 그룹핑)
    theme_days = {}  # normalized_name -> [day_index, ...]
    theme_original = {}  # normalized_name -> 원본 이름 (첫 등장 기준)
    for day_idx, entry in enumerate(sorted_history):
        for theme in entry.get("themes", []):
            name = theme.get("theme_name", "")
            if name:
                normalized = _normalize_theme_name(name)
                theme_days.setdefault(normalized, []).append(day_idx)
                if normalized not in theme_original:
                    theme_original[normalized] = name

    result = []
    for normalized, days in theme_days.items():
        name = theme_original[normalized]
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
