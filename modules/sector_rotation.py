"""섹터 로테이션 감지 모듈

테마 라이프사이클을 4단계(출현→가속→정점→쇠퇴)로 분류합니다.
"""
import re
from typing import Dict, List, Any


def _normalize_theme_name(name: str) -> str:
    """테마명 정규화 (비교용)"""
    name = re.sub(r'\([^)]*\)', '', name)
    name = re.sub(r'[/·・\-]', ' ', name)
    return re.sub(r'\s+', ' ', name).strip()


def detect_sector_rotation(
    theme_history: List[Dict[str, Any]], latest_data: Dict[str, Any]
) -> List[Dict]:
    """테마 라이프사이클 감지

    4단계 모델: 출현(emergence) → 가속(acceleration) → 정점(peak) → 쇠퇴(decline)

    판정 로직:
    - 출현: 최근 2일 내 첫 등장
    - 가속: 3일 연속 등장 + 거래대금 증가 추세
    - 정점: 5일 이상 등장 + 거래대금 감소 시작
    - 쇠퇴: 등장 빈도 감소 + 거래대금 하락
    """
    if not theme_history:
        return []

    sorted_history = sorted(theme_history, key=lambda x: x.get("date", ""))
    total_days = len(sorted_history)

    # 테마별 등장 일자 인덱스 수집 (정규화된 이름으로 그룹핑)
    theme_days = {}
    theme_original = {}  # normalized → 원본 이름
    for day_idx, entry in enumerate(sorted_history):
        for theme in entry.get("themes", []):
            name = theme.get("theme_name", "")
            if name:
                normalized = _normalize_theme_name(name)
                theme_days.setdefault(normalized, []).append(day_idx)
                if normalized not in theme_original:
                    theme_original[normalized] = name

    # 전일 거래대금 데이터 (테마→대장주 코드 매핑은 latest_data에서 추출)
    tv_data = {}
    for market in ["kospi", "kosdaq"]:
        for s in latest_data.get("trading_value", {}).get(market, []):
            code = s.get("code", "")
            if code:
                tv_data[code] = s.get("trading_value", 0)

    # 히스토리에서 전전일 거래대금 추출 (비교 기준)
    prev_tv_data = {}
    if len(sorted_history) >= 2:
        prev_entry = sorted_history[-2]  # 전전일
        for theme in prev_entry.get("themes", []):
            for s in theme.get("leader_stocks", []):
                code = s.get("code", "")
                if code:
                    # 히스토리에 거래대금이 있으면 사용
                    tv = s.get("trading_value", 0)
                    if tv:
                        prev_tv_data[code] = tv

    # 전일 테마 → 대장주 코드 매핑
    theme_stocks = {}
    theme_analysis = latest_data.get("theme_analysis", {})
    for theme in theme_analysis.get("themes", []):
        name = theme.get("theme_name", "")
        codes = [s.get("code", "") for s in theme.get("leader_stocks", []) if s.get("code")]
        if name and codes:
            theme_stocks[name] = codes

    result = []
    for normalized, days in theme_days.items():
        name = theme_original[normalized]
        sorted_days = sorted(days)
        days_active = len(sorted_days)
        last_day = max(sorted_days)

        # 연속 등장일 계산
        max_streak = 1
        current_streak = 1
        for i in range(1, len(sorted_days)):
            if sorted_days[i] == sorted_days[i - 1] + 1:
                current_streak += 1
                max_streak = max(max_streak, current_streak)
            else:
                current_streak = 1

        # 최근성 (마지막 등장이 가장 최근일인지)
        is_recent = last_day >= total_days - 2

        # 거래대금 추세 (전일 vs 전전일 비교)
        codes = theme_stocks.get(name, [])
        total_tv = sum(tv_data.get(c, 0) for c in codes)
        total_prev_tv = sum(prev_tv_data.get(c, 0) for c in codes)

        if total_tv == 0:
            volume_trend = "N/A"
        elif total_prev_tv == 0:
            volume_trend = "N/A"  # 비교 기준 없음
        else:
            change_ratio = (total_tv - total_prev_tv) / total_prev_tv
            if change_ratio > 0.1:
                volume_trend = "상승"
            elif change_ratio < -0.1:
                volume_trend = "하락"
            else:
                volume_trend = "보합"

        # 4단계 판정
        if days_active <= 2 and is_recent:
            phase = "출현"
            signal = "신규 테마 등장"
        elif max_streak >= 3 and is_recent and total_tv > 0:
            if days_active >= 5:
                phase = "정점"
                signal = "장기 등장 + 주의 필요"
                # 마지막 2일 연속이 아니면 쇠퇴
                if last_day < total_days - 1:
                    phase = "쇠퇴"
                    signal = "등장 빈도 감소"
            else:
                phase = "가속"
                signal = "연속 등장 + 모멘텀 지속"
        elif days_active >= 5 and not is_recent:
            phase = "쇠퇴"
            signal = "등장 빈도 감소"
        elif days_active >= 5 and is_recent:
            phase = "정점"
            signal = "장기 등장 + 모멘텀 둔화 가능"
        else:
            phase = "출현"
            signal = "초기 단계"

        result.append({
            "theme_name": name,
            "phase": phase,
            "signal": signal,
            "days_active": days_active,
            "volume_trend": volume_trend,
        })

    # 활동일 기준 내림차순
    result.sort(key=lambda x: x["days_active"], reverse=True)
    return result
