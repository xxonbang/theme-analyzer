"""
종목별 최근 N일간 등락률 계산 모듈
"""
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

from modules.kis_client import KISClient


class StockHistoryAPI:
    """종목별 일별 시세 및 등락률 계산"""

    def __init__(self, client: KISClient = None):
        """
        Args:
            client: KIS 클라이언트 (없으면 새로 생성)
        """
        self.client = client or KISClient()

    def get_recent_changes(
        self,
        stock_code: str,
        days: int = 3,
    ) -> Dict[str, Any]:
        """최근 N일간 등락률 조회

        Args:
            stock_code: 종목코드
            days: 조회할 일수 (기본 3일)

        Returns:
            {
                "code": "005930",
                "changes": [
                    {"date": "2026-01-31", "close": 70000, "change_rate": 2.5},
                    {"date": "2026-01-30", "close": 68300, "change_rate": -1.2},
                    {"date": "2026-01-29", "close": 69100, "change_rate": 0.8},
                ],
                "total_change_rate": 2.1  # 3일간 총 등락률
            }
        """
        try:
            result = self.client.get_stock_daily_price(stock_code)

            if result.get("rt_cd") != "0":
                return {"code": stock_code, "changes": [], "total_change_rate": 0}

            output2 = result.get("output2", [])

            # KIS API는 1회 최대 100건 반환 → MA120 계산에 120건 이상 필요
            if len(output2) >= 100:
                oldest_date = output2[-1].get("stck_bsop_date", "")
                if oldest_date:
                    try:
                        oldest_dt = datetime.strptime(oldest_date, "%Y%m%d")
                        new_end = (oldest_dt - timedelta(days=1)).strftime("%Y%m%d")
                        new_start = (oldest_dt - timedelta(days=180)).strftime("%Y%m%d")
                        result2 = self.client.get_stock_daily_price(
                            stock_code, start_date=new_start, end_date=new_end
                        )
                        if result2.get("rt_cd") == "0":
                            extra = result2.get("output2", [])
                            if extra:
                                output2 = output2 + extra
                    except Exception:
                        pass  # 추가 조회 실패 시 기존 100건만 사용

            if len(output2) < days + 1:
                # 데이터가 부족한 경우
                return {"code": stock_code, "changes": [], "total_change_rate": 0}

            changes = []
            for i in range(days):
                today = output2[i]
                yesterday = output2[i + 1]

                today_close = int(today.get("stck_clpr", 0))
                yesterday_close = int(yesterday.get("stck_clpr", 0))

                if yesterday_close > 0:
                    change_rate = ((today_close - yesterday_close) / yesterday_close) * 100
                else:
                    change_rate = 0

                date_str = today.get("stck_bsop_date", "")
                formatted_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}" if len(date_str) == 8 else date_str

                changes.append({
                    "date": formatted_date,
                    "close": today_close,
                    "change_rate": round(change_rate, 2),
                })

            # 3일간 총 등락률 계산 (첫날 종가 vs N일 전 종가)
            if len(output2) > days:
                latest_close = int(output2[0].get("stck_clpr", 0))
                base_close = int(output2[days].get("stck_clpr", 0))
                if base_close > 0:
                    total_change_rate = ((latest_close - base_close) / base_close) * 100
                else:
                    total_change_rate = 0
            else:
                total_change_rate = 0

            return {
                "code": stock_code,
                "changes": changes,
                "total_change_rate": round(total_change_rate, 2),
                "raw_daily_prices": output2,  # RSI 계산용 raw 데이터
            }

        except Exception as e:
            print(f"[ERROR] 등락률 조회 실패 ({stock_code}): {e}")
            return {"code": stock_code, "changes": [], "total_change_rate": 0, "raw_daily_prices": []}

    def get_multiple_stocks_history(
        self,
        stocks: List[Dict[str, Any]],
        days: int = 3,
    ) -> Dict[str, Dict[str, Any]]:
        """여러 종목의 등락률 일괄 조회

        Args:
            stocks: 종목 리스트 [{"code": ..., "name": ...}, ...]
            days: 조회할 일수

        Returns:
            {종목코드: {"changes": [...], "total_change_rate": ...}, ...}
        """
        result = {}

        for stock in stocks:
            code = stock.get("code", "")
            if not code:
                continue

            history = self.get_recent_changes(code, days)
            result[code] = history

        return result
