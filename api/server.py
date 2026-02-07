"""
FastAPI 서버 - KIS API 실시간 호출 엔드포인트
Refresh 버튼 클릭 시 최신 주식 데이터를 실시간으로 수집하여 반환
"""
import os
import sys
from datetime import datetime, timezone, timedelta

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 프로젝트 루트를 sys.path에 추가 (모듈 import 위해)
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from modules.kis_client import KISClient
from modules.kis_rank import KISRankAPI
from modules.stock_filter import StockFilter
from modules.stock_history import StockHistoryAPI
from modules.exchange_rate import ExchangeRateAPI
from modules.data_exporter import _strip_meta
from main import collect_all_stocks

KST = timezone(timedelta(hours=9))

app = FastAPI(title="Stock TOP10 API", version="1.0.0")

# CORS 설정
ALLOWED_ORIGINS = os.environ.get("CORS_ORIGINS", "").split(",")
ALLOWED_ORIGINS = [o.strip() for o in ALLOWED_ORIGINS if o.strip()]
# 기본 허용 도메인
ALLOWED_ORIGINS += [
    "http://localhost:5173",
    "http://localhost:4173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    """헬스체크 (keep-alive ping용)"""
    return {"status": "ok", "timestamp": datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S")}


@app.get("/api/refresh")
def refresh():
    """실시간 데이터 수집 - latest.json과 동일한 구조 반환

    main.py의 step 1~9를 실행 (뉴스/텔레그램 제외)
    """
    errors = []

    # 1. 환율 정보 조회
    exchange_data = {}
    try:
        exchange_api = ExchangeRateAPI()
        exchange_data = exchange_api.get_exchange_rates()
    except Exception as e:
        errors.append(f"환율 조회 실패: {e}")

    # 2. KIS API 연결
    try:
        client = KISClient()
        rank_api = KISRankAPI(client)
        history_api = StockHistoryAPI(client)
    except Exception as e:
        return {"error": f"KIS API 연결 실패: {e}", "errors": errors}

    # 3. 거래량 TOP30
    try:
        volume_data = rank_api.get_top30_by_volume(exclude_etf=True)
    except Exception as e:
        return {"error": f"거래량 조회 실패: {e}", "errors": errors}

    # 4. 거래대금 TOP30
    trading_value_data = {}
    try:
        trading_value_data = rank_api.get_top30_by_trading_value(exclude_etf=True)
    except Exception as e:
        errors.append(f"거래대금 조회 실패: {e}")

    # 5. 등락폭 TOP30 (자체 계산)
    try:
        fluctuation_data = rank_api.get_top30_by_fluctuation(exclude_etf=True)
    except Exception as e:
        return {"error": f"등락폭 조회 실패: {e}", "errors": errors}

    # 6. 등락률 전용 API
    fluctuation_direct_data = {}
    try:
        fluctuation_direct_data = rank_api.get_top_fluctuation_direct(exclude_etf=True)
    except Exception as e:
        errors.append(f"등락률 전용 API 실패: {e}")

    # 7. 교차 필터링
    stock_filter = StockFilter()
    rising_stocks = stock_filter.filter_rising_stocks(volume_data, fluctuation_data)
    falling_stocks = stock_filter.filter_falling_stocks(volume_data, fluctuation_data)

    # 전체 종목 리스트 (중복 제거)
    all_stocks = collect_all_stocks(
        rising_stocks, falling_stocks,
        volume_data=volume_data,
        trading_value_data=trading_value_data,
        fluctuation_data=fluctuation_data,
        fluctuation_direct_data=fluctuation_direct_data,
    )

    # 8. 3일간 등락률 조회
    history_data = {}
    try:
        history_data = history_api.get_multiple_stocks_history(all_stocks, days=3)
    except Exception as e:
        errors.append(f"등락률 조회 실패: {e}")

    # 9. 수급(투자자) 데이터
    investor_data = {}
    try:
        investor_data = rank_api.get_investor_data(all_stocks)
    except Exception as e:
        errors.append(f"수급 데이터 수집 실패: {e}")

    # latest.json과 동일한 구조로 반환
    data = {
        "timestamp": datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S"),
        "exchange": exchange_data or {},
        "rising": {
            "kospi": rising_stocks.get("kospi", []),
            "kosdaq": rising_stocks.get("kosdaq", []),
        },
        "falling": {
            "kospi": falling_stocks.get("kospi", []),
            "kosdaq": falling_stocks.get("kosdaq", []),
        },
        "volume": _strip_meta(volume_data) if volume_data else None,
        "trading_value": _strip_meta(trading_value_data) if trading_value_data else None,
        "fluctuation": _strip_meta(fluctuation_data) if fluctuation_data else None,
        "fluctuation_direct": _strip_meta(fluctuation_direct_data) if fluctuation_direct_data else None,
        "history": history_data,
        "news": {},
        "investor_data": investor_data if investor_data else None,
    }

    # None 값 필드 제거
    data = {k: v for k, v in data.items() if v is not None}

    if errors:
        data["_warnings"] = errors

    return data
