"""
API Key, 환경 설정, 타겟 거래소 설정
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# 프로젝트 루트 경로
ROOT_DIR = Path(__file__).parent.parent

# .env 파일 로드
load_dotenv(ROOT_DIR / ".env")

# Gemini API Keys (3개 로테이션)
GEMINI_API_KEYS = [
    os.getenv("GEMINI_API_KEY_01"),
    os.getenv("GEMINI_API_KEY_02"),
    os.getenv("GEMINI_API_KEY_03"),
]
GEMINI_API_KEYS = [k for k in GEMINI_API_KEYS if k]  # None 제거

# 타겟 URL (신버전 stock.naver.com)
KOSPI_API_URL = "https://stock.naver.com/api/domestic/market/stock/default?tradeType=KRX&marketType=KOSPI&orderType=quantTop&startIdx=0&pageSize=50"
KOSDAQ_API_URL = "https://stock.naver.com/api/domestic/market/stock/default?tradeType=KRX&marketType=KOSDAQ&orderType=quantTop&startIdx=0&pageSize=70"
STOCK_DETAIL_URL = "https://stock.naver.com/domestic/stock/{code}"

# 스크래핑 설정
MAX_KOSPI_STOCKS = 50
MAX_KOSDAQ_STOCKS = 70
MAX_STOCKS_PER_MARKET = 50  # 하위 호환성 유지
VIEWPORT_WIDTH = 1920
VIEWPORT_HEIGHT = 1080
DEVICE_SCALE_FACTOR = 2

# User-Agent (봇 탐지 우회)
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# 캡처/출력 경로
CAPTURES_DIR = ROOT_DIR / "captures"
OUTPUT_DIR = ROOT_DIR / "output"

# AI 설정
GEMINI_MODEL = "gemini-2.5-flash"

# 시그널 카테고리
SIGNAL_CATEGORIES = ["적극매수", "매수", "중립", "매도", "적극매도"]
