"""
KST 기준 장중 여부 판별 유틸리티
- 평일 09:00~15:30 KST → True
- 주말, 공휴일 → False
"""
from datetime import datetime

from modules.utils import KST

# 2026년 KRX 휴장일 (매년 갱신 필요)
KRX_HOLIDAYS_2026 = {
    "2026-01-01",  # 신정
    "2026-01-27",  # 대체공휴일(설날)
    "2026-01-28",  # 설날 연휴
    "2026-01-29",  # 설날
    "2026-01-30",  # 설날 연휴
    "2026-03-01",  # 삼일절
    "2026-03-02",  # 대체공휴일(삼일절)
    "2026-05-05",  # 어린이날
    "2026-05-24",  # 부처님오신날
    "2026-06-06",  # 현충일
    "2026-08-15",  # 광복절
    "2026-08-17",  # 대체공휴일(광복절)
    "2026-09-24",  # 추석 연휴
    "2026-09-25",  # 추석
    "2026-09-26",  # 추석 연휴
    "2026-10-03",  # 개천절
    "2026-10-05",  # 대체공휴일(개천절)
    "2026-10-09",  # 한글날
    "2026-12-25",  # 크리스마스
    "2026-12-31",  # 연말 임시공휴일 (확정 시 추가)
}


def is_market_hours(dt: datetime = None) -> bool:
    """KST 기준 장중 여부 판별

    Args:
        dt: 판별할 시각 (None이면 현재 시각 사용)

    Returns:
        True if 장중 (평일 09:00~15:30 KST), False otherwise
    """
    if dt is None:
        dt = datetime.now(KST)
    elif dt.tzinfo is None:
        dt = dt.replace(tzinfo=KST)

    # 주말 체크 (0=월 ~ 6=일)
    if dt.weekday() >= 5:
        return False

    # 공휴일 체크
    date_str = dt.strftime("%Y-%m-%d")
    if date_str in KRX_HOLIDAYS_2026:
        return False

    # 시간 체크: 09:00 <= time < 15:30
    t = dt.hour * 60 + dt.minute
    return 540 <= t < 930  # 09:00=540, 15:30=930
