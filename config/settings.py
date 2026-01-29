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

# 타겟 URL (모바일 버전 m.stock.naver.com - 더 많은 정보 표시)
KOSPI_API_URL = "https://stock.naver.com/api/domestic/market/stock/default?tradeType=KRX&marketType=KOSPI&orderType=quantTop&startIdx=0&pageSize=50"
KOSDAQ_API_URL = "https://stock.naver.com/api/domestic/market/stock/default?tradeType=KRX&marketType=KOSDAQ&orderType=quantTop&startIdx=0&pageSize=70"
STOCK_DETAIL_URL = "https://m.stock.naver.com/domestic/stock/{code}/total"

# 스크래핑 설정 (태블릿 뷰포트 - iPad Pro 11")
MAX_KOSPI_STOCKS = 50
MAX_KOSDAQ_STOCKS = 70
MAX_STOCKS_PER_MARKET = 50  # 하위 호환성 유지
VIEWPORT_WIDTH = 834   # iPad Pro 11" 너비
VIEWPORT_HEIGHT = 1194 # iPad Pro 11" 높이
DEVICE_SCALE_FACTOR = 2

# User-Agent (iPad)
USER_AGENT = "Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"

# 캡처/출력 경로
CAPTURES_DIR = ROOT_DIR / "captures"
OUTPUT_DIR = ROOT_DIR / "output"

# AI 설정
GEMINI_MODEL = "gemini-2.5-flash"

# 시그널 카테고리
SIGNAL_CATEGORIES = ["적극매수", "매수", "중립", "매도", "적극매도"]

# 한국투자증권 API 설정
# 주의: 순위분석 API는 모의투자에서 지원되지 않으므로 실전투자만 사용
KIS_APP_KEY = os.getenv("KIS_APP_KEY")
KIS_APP_SECRET = os.getenv("KIS_APP_SECRET")
KIS_ACCOUNT_NO = os.getenv("KIS_ACCOUNT_NO")  # 계좌번호 (XXXXXXXX-XX 형식)

# KIS API 엔드포인트 (실전투자 전용)
KIS_BASE_URL = "https://openapi.koreainvestment.com:9443"

# KIS API 결과 저장 경로
KIS_OUTPUT_DIR = ROOT_DIR / "results" / "kis"
