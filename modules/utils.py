"""공통 유틸리티 모듈

여러 모듈에서 공통으로 사용하는 타입 변환 함수 및 상수.
"""

from datetime import timezone, timedelta
from typing import Optional


# ── 타임존 ─────────────────────────────────────────────────
KST = timezone(timedelta(hours=9))


# ── 타입 변환 (기본값 반환) ─────────────────────────────────
def safe_int(value, default: int = 0) -> int:
    """빈 문자열이나 None을 안전하게 정수로 변환"""
    if value is None or value == "":
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def safe_float(value, default: float = 0.0) -> float:
    """빈 문자열이나 None을 안전하게 실수로 변환"""
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


# ── 타입 변환 (None 반환) ──────────────────────────────────
def safe_int_or_none(value) -> Optional[int]:
    """빈 문자열이나 None이면 None 반환"""
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def safe_float_or_none(value) -> Optional[float]:
    """빈 문자열이나 None이면 None 반환, 0도 None 처리 (재무 데이터용)"""
    if value is None or value == "":
        return None
    try:
        v = float(value)
        return v if v != 0 else None
    except (ValueError, TypeError):
        return None
