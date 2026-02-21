"""예측 백테스팅 모듈

Supabase의 theme_predictions에서 active 예측을 조회하고,
실제 주가 수익률을 비교하여 적중 여부를 판정합니다.
"""
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from modules.utils import KST


def get_active_predictions(client) -> List[Dict]:
    """Supabase에서 status='active' 예측 조회"""
    response = client.table("theme_predictions").select("*").eq(
        "status", "active"
    ).execute()
    return response.data or []


def fetch_stock_returns(codes: List[str], start: str, end: str) -> Dict:
    """yfinance로 한국 주식 수익률 조회

    Args:
        codes: 종목코드 리스트 (예: ["005930", "000660"])
        start: 시작일 YYYY-MM-DD
        end: 종료일 YYYY-MM-DD

    Returns:
        {code: return_pct} 딕셔너리
    """
    try:
        import yfinance as yf
    except ImportError:
        print("  ⚠ yfinance 미설치")
        return {}

    returns = {}
    # 코스피(.KS) 먼저 시도, 실패 시 코스닥(.KQ) 시도
    for code in codes:
        for suffix in [".KS", ".KQ"]:
            ticker = f"{code}{suffix}"
            try:
                data = yf.download(ticker, start=start, end=end, progress=False)
                if data.empty or len(data) < 2:
                    continue
                close = data["Close"]
                first_price = float(close.iloc[0])
                last_price = float(close.iloc[-1])
                if first_price > 0:
                    returns[code] = round(((last_price - first_price) / first_price) * 100, 2)
                    break
            except Exception:
                continue

    return returns


def fetch_index_return(start: str, end: str) -> float:
    """KOSPI 지수 수익률 조회"""
    try:
        import yfinance as yf
        data = yf.download("^KS11", start=start, end=end, progress=False)
        if data.empty or len(data) < 2:
            return 0.0
        close = data["Close"]
        first_val = float(close.iloc[0])
        last_val = float(close.iloc[-1])
        if first_val > 0:
            return round(((last_val - first_val) / first_val) * 100, 2)
    except Exception:
        pass
    return 0.0


def evaluate_prediction(prediction: Dict, returns: Dict, index_return: float) -> str:
    """단일 예측 평가

    hit 기준: 대장주 중 1개 이상이 해당 기간 내 지수 대비 +1%p 초과 수익
    """
    category = prediction.get("category", "today")
    prediction_date = prediction.get("prediction_date", "")

    if not prediction_date:
        return "active"

    pred_date = datetime.strptime(prediction_date, "%Y-%m-%d")
    now = datetime.now(KST).replace(tzinfo=None)
    days_elapsed = (now - pred_date).days

    # 카테고리별 판정 기간
    max_days = {"today": 1, "short_term": 7, "long_term": 30}.get(category, 7)

    if days_elapsed < max_days:
        return "active"  # 아직 판정 불가

    # 대장주 수익률 확인
    leader_stocks = prediction.get("leader_stocks", "[]")
    if isinstance(leader_stocks, str):
        try:
            leader_stocks = json.loads(leader_stocks)
        except json.JSONDecodeError:
            leader_stocks = []

    stock_codes = [s.get("code", "") for s in leader_stocks if s.get("code")]
    if not stock_codes:
        return "expired"

    # 수익률 데이터가 있는 종목 중 하나라도 지수 대비 +1%p 초과면 hit
    for code in stock_codes:
        stock_return = returns.get(code)
        if stock_return is not None:
            excess = stock_return - index_return
            if excess > 1.0:
                return "hit"

    # 모든 종목의 수익률 데이터가 없으면 expired
    has_any_return = any(code in returns for code in stock_codes)
    if not has_any_return:
        return "expired"

    return "missed"


def update_prediction_status(client, pred_id: int, status: str, performance: Dict):
    """Supabase status + actual_performance 업데이트"""
    update_data = {
        "status": status,
        "evaluated_at": datetime.now(KST).isoformat(),
        "actual_performance": json.dumps(performance, ensure_ascii=False),
    }
    client.table("theme_predictions").update(update_data).eq("id", pred_id).execute()


def calculate_accuracy_report(client) -> Dict:
    """신뢰도별/카테고리별 적중률 집계"""
    response = client.table("theme_predictions").select("*").in_(
        "status", ["hit", "missed"]
    ).execute()

    data = response.data or []
    if not data:
        return {"total": 0, "hit": 0, "accuracy": 0.0, "by_confidence": {}, "by_category": {}}

    total = len(data)
    hits = sum(1 for d in data if d.get("status") == "hit")

    by_confidence = {}
    by_category = {}

    for d in data:
        confidence = d.get("confidence", "N/A")
        category = d.get("category", "N/A")
        is_hit = d.get("status") == "hit"

        for group, key in [(by_confidence, confidence), (by_category, category)]:
            if key not in group:
                group[key] = {"total": 0, "hit": 0}
            group[key]["total"] += 1
            if is_hit:
                group[key]["hit"] += 1

    for group in [by_confidence, by_category]:
        for v in group.values():
            v["accuracy"] = round(v["hit"] / v["total"] * 100, 1) if v["total"] else 0.0

    return {
        "total": total,
        "hit": hits,
        "accuracy": round(hits / total * 100, 1) if total else 0.0,
        "by_confidence": by_confidence,
        "by_category": by_category,
    }
