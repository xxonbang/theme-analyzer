"""
유망 테마 예측 모듈

장 개장 전(7:30 AM) 전일 데이터 + Google Search를 기반으로
오늘/단기/장기 유망 테마를 예측합니다.
"""
import json
import re
import time
import requests
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

from config.settings import GEMINI_API_KEY_1, GEMINI_API_KEY_2, GEMINI_API_KEY_3
from modules.utils import KST

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
ROOT_DIR = Path(__file__).parent.parent


def _get_api_keys() -> List[str]:
    """사용 가능한 API 키 목록 반환"""
    keys = [GEMINI_API_KEY_1, GEMINI_API_KEY_2, GEMINI_API_KEY_3]
    return [k for k in keys if k]


def _extract_json(text: str) -> Optional[Dict]:
    """응답 텍스트에서 JSON 블록 추출"""
    match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    if match:
        return json.loads(match.group(1))
    match = re.search(r"```\s*(.*?)\s*```", text, re.DOTALL)
    if match:
        candidate = match.group(1).strip()
        if candidate.startswith("{"):
            return json.loads(candidate)
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return json.loads(match.group(0))
    return None


def _call_gemini(prompt: str, api_key: str) -> Optional[Dict]:
    """Gemini API 호출 (Google Search grounding)"""
    url = f"{GEMINI_API_URL}?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "tools": [{"google_search": {}}],
        "generationConfig": {
            "temperature": 0.5,
        },
    }

    resp = requests.post(url, json=payload, timeout=120)
    resp.raise_for_status()

    data = resp.json()
    candidates = data.get("candidates", [])
    if not candidates:
        return None

    content = candidates[0].get("content", {})
    parts = content.get("parts", [])

    text = ""
    for part in parts:
        if "text" in part:
            text += part["text"]

    if not text.strip():
        return None

    return _extract_json(text)


def build_forecast_context(latest_data: Dict[str, Any], theme_history: List[Dict[str, Any]]) -> str:
    """Gemini 입력용 예측 컨텍스트 구성

    Args:
        latest_data: 전일 latest.json 데이터
        theme_history: 최근 7일간 테마 분석 이력 [{date, themes: [...]}]
    """
    lines = []

    # 1. 전일 테마 분석 결과
    theme_analysis = latest_data.get("theme_analysis")
    if theme_analysis:
        lines.append("## 전일 테마 분석 결과")
        lines.append(f"분석일: {theme_analysis.get('analysis_date', 'N/A')}")
        lines.append(f"시장 요약: {theme_analysis.get('market_summary', 'N/A')}")
        for theme in theme_analysis.get("themes", []):
            leaders = ", ".join(
                f"{s.get('name')}({s.get('code')})" for s in theme.get("leader_stocks", [])
            )
            lines.append(f"- 테마: {theme.get('theme_name')} | 대장주: {leaders}")
            lines.append(f"  설명: {theme.get('theme_description', '')}")

    # 2. 최근 7일 테마 흐름
    if theme_history:
        lines.append("\n## 최근 7일 테마 흐름")
        for entry in theme_history:
            date = entry.get("date", "N/A")
            themes = entry.get("themes", [])
            theme_names = [t.get("theme_name", "") for t in themes]
            lines.append(f"- {date}: {', '.join(theme_names)}")

    # 3. 전일 시장 환경
    lines.append("\n## 전일 시장 환경")

    # 코스닥 지수
    kosdaq = latest_data.get("kosdaq_index")
    if kosdaq:
        lines.append(f"- 코스닥 지수: {kosdaq.get('current', 0):.2f} ({kosdaq.get('status', 'N/A')})")

    # 환율
    exchange = latest_data.get("exchange")
    if exchange:
        rates = exchange.get("rates", [])
        for r in rates:
            lines.append(f"- 환율 {r.get('currency', '')}: {r.get('deal_rate', 'N/A')}")

    # 4. 전일 거래대금 TOP10 + 수급
    tv_kospi = latest_data.get("trading_value", {}).get("kospi", [])[:10]
    tv_kosdaq = latest_data.get("trading_value", {}).get("kosdaq", [])[:10]
    investor_data = latest_data.get("investor_data", {})

    if tv_kospi or tv_kosdaq:
        lines.append("\n## 전일 거래대금 TOP10 + 수급")
        for s in tv_kospi + tv_kosdaq:
            code = s.get("code", "")
            tv = s.get("trading_value", 0)
            tv_str = f"{tv / 100_000_000:,.0f}억원" if tv else "N/A"
            market = "코스피" if s in tv_kospi else "코스닥"
            inv = investor_data.get(code, {})
            foreign = inv.get("foreign_net")
            institution = inv.get("institution_net")
            inv_parts = []
            if foreign and foreign != 0:
                sign = "+" if foreign > 0 else ""
                inv_parts.append(f"외국인:{sign}{foreign:,}주")
            if institution and institution != 0:
                sign = "+" if institution > 0 else ""
                inv_parts.append(f"기관:{sign}{institution:,}주")
            inv_str = f" | {' '.join(inv_parts)}" if inv_parts else ""
            lines.append(
                f"- {s.get('name')}({code}) {market} 등락:{s.get('change_rate', 0):+.2f}% "
                f"거래대금:{tv_str}{inv_str}"
            )

    # 5. 전일 테마별 대장주 상세 (대장주 선정 근거용)
    if theme_analysis:
        criteria_data = latest_data.get("criteria_data", {})
        lines.append("\n## 전일 테마 대장주 상세 데이터")
        for theme in theme_analysis.get("themes", []):
            lines.append(f"\n### {theme.get('theme_name')}")
            for stock in theme.get("leader_stocks", []):
                code = stock.get("code", "")
                inv = investor_data.get(code, {})
                criteria = criteria_data.get(code, {})

                parts = [f"{stock.get('name')}({code})"]
                # 수급
                foreign = inv.get("foreign_net")
                if foreign and foreign != 0:
                    parts.append(f"외국인:{'+'if foreign>0 else ''}{foreign:,}주")
                institution = inv.get("institution_net")
                if institution and institution != 0:
                    parts.append(f"기관:{'+'if institution>0 else ''}{institution:,}주")
                # 정배열 여부
                ma = criteria.get("ma_alignment", {})
                if isinstance(ma, dict) and ma.get("met"):
                    parts.append("정배열")

                lines.append(f"- {' | '.join(parts)}")

    return "\n".join(lines)


def _build_forecast_prompt(context: str) -> str:
    """유망 테마 예측 Gemini 프롬프트 생성"""
    today = datetime.now(KST).strftime("%Y년 %m월 %d일")
    today_search = datetime.now(KST).strftime("%m월 %d일")

    return f"""당신은 대한민국 주식시장 테마 예측 전문 애널리스트입니다.
전일 시장 데이터와 실시간 뉴스를 기반으로 향후 유망 테마를 예측합니다.

오늘은 {today}이며, 장 개장 전(오전 7:30) 기준입니다.
아래는 전일 시장 데이터와 최근 테마 흐름입니다:

{context}

### Google Search 지시 — 정확히 3건만 검색하세요

**검색 1: "미국 증시 마감 {today_search}"**
추출 절차:
  1단계: 미국 시장에서 실제로 크게 움직인 섹터/종목을 사실 그대로 추출 (상승 상위 2~3개 섹터, 하락 상위 2~3개 섹터)
  2단계: 각 움직임의 원인(촉매)을 파악
  3단계: 해당 원인이 한국 주식시장의 어떤 테마/섹터에 파급효과를 줄 수 있는지 인과관계를 스스로 도출
  4단계: 인과관계가 명확한 항목만 채택, 불명확하면 제외
※ 특정 업종에 국한하지 말 것. 검색 결과에서 실제로 움직인 내용을 기반으로 테마를 동적으로 도출할 것.
※ 인과관계 예시 (참고용, 이 예시에 한정하지 말 것):
  - 미국 필라델피아 반도체 지수 +3% → 한국 반도체 관련주 수혜 가능
  - 국제 유가 급등 → 한국 정유/에너지 테마 부각 가능
  - 미국 바이오텍 FDA 승인 뉴스 → 한국 바이오 심리 개선 가능

**검색 2: "한국 증시 전망 {today_search}"**
추출 절차:
  1단계: 증권사 리포트/뉴스에서 언급된 구체적 테마 키워드 추출
  2단계: 각 테마의 부각 배경(촉매)을 파악
  3단계: 전일 테마와의 연속성 또는 신규성 판단
※ "혼조세 예상", "관망세 지속" 등 방향성 없는 일반론은 제외
※ 구체적 섹터/종목이 언급된 경우만 채택

**검색 3: "한국 경제 일정 이번주" 또는 "한국 경제 일정 이번달"**
추출 절차:
  1단계: 향후 1개월 내 주요 이벤트 목록 추출
  2단계: 각 이벤트가 영향을 미칠 테마/섹터를 스스로 도출
  3단계: 영향도가 높은 이벤트만 채택
※ 일상적/반복적 이벤트는 특별한 이슈가 없으면 제외
※ 이벤트 → 테마 인과관계를 반드시 명시

### 제외 규칙
- 구체적 테마/섹터로 연결되지 않는 일반 시장 전망
- "불안정", "관망세" 같은 방향성 없는 코멘터리
- 한국 주식시장과 인과관계가 불분명한 해외 뉴스
- 이미 전일 테마에 반영 완료되어 추가 모멘텀이 없는 재탕 뉴스

### 대장주 선정 규칙
- 각 테마당 최대 3개 종목, priority 값으로 우선순위 차별화
- priority 값은 반드시 아래 기준에 따라 1, 2, 3 중 하나를 부여 (모두 같은 값 금지):
  priority 1: 전일 해당 테마 거래대금 최상위 + 외국인/기관 동반 순매수 → 핵심 대장주
  priority 2: 전일 해당 테마 거래대금 상위이나 수급 조건 부분 충족 → 주요 관련주
  priority 3: 테마 대표성은 높으나 전일 거래대금/수급 데이터 미흡 → 관련주
- 3개 종목 선정 시 priority는 반드시 1, 2, 3으로 차등 배분할 것 (예: 1, 2, 3 또는 1, 1, 2)
- priority 3 종목이면서 전일 데이터 미확인 시 data_verified를 false로 설정
- 종목 선정 시 반드시 Google Search로 "종목명 테마명 2026" 검색하여 해당 종목이 실제로 이 테마와 관련 있는지 교차 검증

### 출력 형식
반드시 아래 JSON 형식으로만 응답하세요 (다른 텍스트 없이 JSON만):
```json
{{
  "market_context": "전일 시장 환경 + 미국 시장 영향 요약 (2~3문장)",
  "us_market_summary": "미국 시장 마감 요약 (S&P500, 나스닥 등락률 + 주요 섹터 동향)",
  "today": [
    {{
      "theme_name": "테마명",
      "description": "이 테마가 오늘 부각될 것으로 예상되는 구체적 배경과 촉매",
      "catalyst": "핵심 촉매 이벤트 1줄 요약",
      "confidence": "높음|보통|낮음",
      "leader_stocks": [
        {{"priority": 1, "name": "핵심 대장주", "code": "000000", "reason": "선정 근거 — 거래대금 1위 + 외국인/기관 동반 순매수", "data_verified": true}},
        {{"priority": 2, "name": "주요 관련주", "code": "000001", "reason": "선정 근거 — 거래대금 상위 + 수급 부분 충족", "data_verified": true}},
        {{"priority": 3, "name": "관련주", "code": "000002", "reason": "선정 근거 — 테마 대표성 높음", "data_verified": false}}
      ]
    }}
  ],
  "short_term": [
    {{
      "theme_name": "테마명",
      "description": "단기 부각 예상 배경",
      "catalyst": "촉매 이벤트",
      "confidence": "높음|보통|낮음",
      "target_period": "2~3일|이번주|7일 이내",
      "leader_stocks": [
        {{
          "priority": 1,
          "name": "종목명",
          "code": "종목코드",
          "reason": "선정 근거",
          "data_verified": true
        }}
      ]
    }}
  ],
  "long_term": [
    {{
      "theme_name": "테마명",
      "description": "장기 부각 예상 배경",
      "catalyst": "촉매 이벤트",
      "confidence": "높음|보통|낮음",
      "target_period": "2주|3주|1개월 이내",
      "leader_stocks": [
        {{
          "priority": 1,
          "name": "종목명",
          "code": "종목코드",
          "reason": "선정 근거",
          "data_verified": false
        }}
      ]
    }}
  ]
}}
```"""


def load_theme_history(history_dir: Path, days: int = 7) -> List[Dict[str, Any]]:
    """최근 N일간 테마 히스토리 로드

    Args:
        history_dir: history 디렉토리 경로
        days: 조회할 일수 (기본 7일)

    Returns:
        [{date: "YYYY-MM-DD", themes: [...]}] 리스트 (최신순)
    """
    if not history_dir.exists():
        return []

    files = sorted(history_dir.glob("*.json"), reverse=True)
    result = []
    seen_dates = set()

    for f in files:
        if len(seen_dates) >= days:
            break
        try:
            date_str = f.stem[:10]  # YYYY-MM-DD
            if date_str in seen_dates:
                continue

            with open(f, "r", encoding="utf-8") as fp:
                data = json.load(fp)

            theme_analysis = data.get("theme_analysis")
            if not theme_analysis or not theme_analysis.get("themes"):
                continue

            result.append({
                "date": date_str,
                "themes": theme_analysis["themes"],
            })
            seen_dates.add(date_str)
        except (json.JSONDecodeError, KeyError):
            continue

    return result


def _fix_leader_priorities(forecast: Dict[str, Any]) -> None:
    """대장주 priority를 순서대로 1, 2, 3으로 강제 재할당

    Gemini가 모두 1로 반환하는 경우가 빈번하므로 후처리로 보정한다.
    """
    for category in ("today", "short_term", "long_term"):
        for theme in forecast.get(category, []):
            stocks = theme.get("leader_stocks", [])
            for idx, stock in enumerate(stocks):
                stock["priority"] = idx + 1


def generate_forecast(latest_data: Dict[str, Any], theme_history: List[Dict[str, Any]]) -> Optional[Dict]:
    """유망 테마 예측 실행

    Args:
        latest_data: 전일 latest.json 데이터
        theme_history: 최근 7일간 테마 히스토리

    Returns:
        예측 결과 dict 또는 실패 시 None
    """
    api_keys = _get_api_keys()
    if not api_keys:
        print("  ⚠ Gemini API 키가 설정되지 않았습니다")
        return None

    context = build_forecast_context(latest_data, theme_history)
    if not context.strip():
        print("  ⚠ 예측 컨텍스트가 비어있습니다")
        return None

    prompt = _build_forecast_prompt(context)
    max_retries_per_key = 3

    for key_idx, api_key in enumerate(api_keys):
        for attempt in range(max_retries_per_key):
            try:
                print(f"  Gemini 예측 API 호출 중... (키 {key_idx + 1}/{len(api_keys)}, 시도 {attempt + 1}/{max_retries_per_key})")
                result = _call_gemini(prompt, api_key)
                if result:
                    now = datetime.now(KST)
                    forecast = {
                        "forecast_date": now.strftime("%Y년 %m월 %d일"),
                        "generated_at": now.strftime("%Y-%m-%d %H:%M:%S"),
                        "market_context": result.get("market_context", ""),
                        "us_market_summary": result.get("us_market_summary", ""),
                        "today": result.get("today", []),
                        "short_term": result.get("short_term", []),
                        "long_term": result.get("long_term", []),
                    }
                    _fix_leader_priorities(forecast)
                    return forecast
                print("  ⚠ Gemini 응답이 비어있습니다")
            except requests.exceptions.HTTPError as e:
                status = e.response.status_code if e.response is not None else 0
                if status in (429, 503):
                    if attempt < max_retries_per_key - 1:
                        wait = 2 ** (attempt + 1)
                        print(f"  ⚠ API 제한 ({status}), {wait}초 후 재시도...")
                        time.sleep(wait)
                        continue
                    else:
                        print(f"  ⚠ 키 {key_idx + 1} 재시도 소진, 다음 키로 전환")
                        break
                else:
                    print(f"  ✗ Gemini API 오류 ({status}): {e}")
                    return None
            except json.JSONDecodeError as e:
                print(f"  ⚠ Gemini 응답 JSON 파싱 실패: {e}")
                if attempt < max_retries_per_key - 1:
                    time.sleep(2)
                    continue
                break
            except Exception as e:
                print(f"  ✗ Gemini API 호출 실패: {e}")
                return None

    print("  ✗ 모든 Gemini API 키로 예측 실패")
    return None


def save_forecast_to_supabase(forecast: Dict[str, Any]) -> bool:
    """예측 결과를 Supabase theme_predictions 테이블에 저장"""
    try:
        from modules.supabase_client import get_supabase_manager
        manager = get_supabase_manager()
        client = manager._get_client()
        if not client:
            print("  ⚠ Supabase 연결 불가, 저장 건너뜀")
            return False

        prediction_date = datetime.now(KST).strftime("%Y-%m-%d")

        # 기존 당일 예측 삭제 (재실행 대응)
        client.table("theme_predictions").delete().eq(
            "prediction_date", prediction_date
        ).execute()

        rows = []
        for category in ("today", "short_term", "long_term"):
            for theme in forecast.get(category, []):
                rows.append({
                    "prediction_date": prediction_date,
                    "category": category,
                    "theme_name": theme.get("theme_name", ""),
                    "description": theme.get("description", ""),
                    "catalyst": theme.get("catalyst", ""),
                    "confidence": theme.get("confidence", ""),
                    "target_period": theme.get("target_period"),
                    "leader_stocks": json.dumps(
                        theme.get("leader_stocks", []), ensure_ascii=False
                    ),
                    "status": "active",
                })

        if rows:
            client.table("theme_predictions").insert(rows).execute()
            print(f"  ✓ Supabase 저장 완료 ({len(rows)}건)")
            return True

        return False
    except Exception as e:
        print(f"  ⚠ Supabase 저장 실패: {e}")
        return False


def export_forecast_json(forecast: Dict[str, Any], output_dir: str = "frontend/public/data") -> str:
    """예측 결과를 JSON 파일로 export

    Returns:
        저장된 파일 경로
    """
    output_path = ROOT_DIR / output_dir
    output_path.mkdir(parents=True, exist_ok=True)

    file_path = output_path / "theme-forecast.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(forecast, f, ensure_ascii=False, indent=2)

    print(f"  ✓ 예측 결과 저장: {file_path}")
    return str(file_path)
