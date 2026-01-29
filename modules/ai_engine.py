"""
Gemini API 연동 및 프롬프트 관리 (배치 처리 방식)
"""
from __future__ import annotations
import time
import base64
from datetime import datetime, timezone, timedelta
from pathlib import Path
from google import genai

# KST 시간대
KST = timezone(timedelta(hours=9))

from config.settings import GEMINI_API_KEYS, GEMINI_MODEL, SIGNAL_CATEGORIES
from modules.utils import parse_json_response, resize_image


# 현재 사용 중인 API 키 인덱스
_current_key_index = 0
_failed_keys = set()


def get_next_api_key() -> tuple[str, int] | None:
    """다음 사용 가능한 API 키 반환"""
    global _current_key_index

    if not GEMINI_API_KEYS:
        print("[ERROR] Gemini API 키가 설정되지 않았습니다.")
        return None

    if len(_failed_keys) >= len(GEMINI_API_KEYS):
        print("[INFO] 모든 키가 실패 상태. 리셋 후 재시도...")
        _failed_keys.clear()

    for _ in range(len(GEMINI_API_KEYS)):
        if _current_key_index not in _failed_keys:
            key = GEMINI_API_KEYS[_current_key_index]
            return key, _current_key_index
        _current_key_index = (_current_key_index + 1) % len(GEMINI_API_KEYS)

    return None


def mark_key_failed(key_index: int):
    """키를 실패 상태로 표시"""
    _failed_keys.add(key_index)
    print(f"  [KEY #{key_index + 1}] 실패. 남은 키: {len(GEMINI_API_KEYS) - len(_failed_keys)}개")


def rotate_to_next_key():
    """다음 키로 로테이션"""
    global _current_key_index
    _current_key_index = (_current_key_index + 1) % len(GEMINI_API_KEYS)


# 배치 분석 프롬프트
BATCH_ANALYSIS_PROMPT = """당신은 20년 경력의 대한민국 주식 시장 전문 퀀트 애널리스트입니다.

아래에 {count}개의 네이버 증권 종목 상세 페이지 스크린샷이 첨부되어 있습니다.
각 이미지에 대해 다음 작업을 수행하세요:

1. **데이터 추출**: 이미지에서 종목명, 종목코드, 현재가, 전일대비, 등락률, 이동평균선(MA), 차트 패턴, 거래량 변화율, 전일, 시가, 종가, 고가, 저가, 거래량, 대금, 시총, 외인소진율, PER, EPS, 추정PER, 추정EPS, PBR, BPS, 배당수익률, 주당배당금, 컨센서스(없는 종목 있음), 목표주가, 차트, 거래량, 호가, 시세, 투자자별 매매동향을 추출
2. **기술적 분석**: 추출한 모든 수치 및 지표와 차트 패턴, 이동평균선, 거래량 등을 분석하여 투자 시그널 결정
3. **시그널 결정**: [적극매수, 매수, 중립, 매도, 적극매도] 중 하나 선택
4. **분석 근거**: 시그널 결정의 근거를 2~3문장으로 설명

종목 목록:
{stock_list}

반드시 아래 JSON 형식으로만 응답하세요. 다른 텍스트 없이 JSON만 출력하세요:
```json
{{
  "results": [
    {{
      "name": "종목명",
      "code": "종목코드",
      "current_price": "현재가",
      "change": "전일대비",
      "change_percent": "등락률",
      "signal": "시그널",
      "reason": "분석 근거 (2~3문장)"
    }}
  ]
}}
```

중요_01: 모든 {count}개 종목에 대해 분석 결과를 반드시 포함해야 합니다.
중요_02: 종목과 해당 종목에 대한 분석 결과가 정확히 매칭되도록 주의하세요.
"""


def analyze_stocks_batch(scrape_results: list[dict], capture_dir: Path, max_retries: int = 3) -> list[dict]:
    """모든 종목 이미지를 한 번에 배치 분석 (API 1회 호출)"""
    print("\n=== Phase 3: AI 배치 분석 ===\n")
    print(f"사용 가능한 API 키: {len(GEMINI_API_KEYS)}개")

    # 성공한 종목만 필터링
    valid_stocks = []
    image_parts = []

    for stock in scrape_results:
        if not stock.get("success"):
            continue

        code = stock["code"]
        image_path = capture_dir / f"{code}.png"

        if not image_path.exists():
            print(f"  [SKIP] {stock['name']}: 이미지 없음")
            continue

        # 이미지 로드 및 리사이즈
        image_bytes = resize_image(image_path)
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")

        valid_stocks.append(stock)
        image_parts.append({
            "inline_data": {
                "mime_type": "image/png",
                "data": image_b64
            }
        })

    if not valid_stocks:
        print("[ERROR] 분석할 종목이 없습니다.")
        return []

    print(f"분석 대상: {len(valid_stocks)}개 종목")
    print(f"총 이미지: {len(image_parts)}개\n")

    # 종목 리스트 문자열 생성
    stock_list_str = "\n".join([
        f"- {i+1}번째 이미지: {s['name']} ({s['code']}) - {s['market']}"
        for i, s in enumerate(valid_stocks)
    ])

    # 프롬프트 생성
    prompt = BATCH_ANALYSIS_PROMPT.format(
        count=len(valid_stocks),
        stock_list=stock_list_str
    )

    # API 호출 시도
    for attempt in range(max_retries):
        key_info = get_next_api_key()
        if not key_info:
            print("[ERROR] 사용 가능한 API 키가 없습니다.")
            return []

        api_key, key_index = key_info
        print(f"[시도 {attempt + 1}/{max_retries}] API 키 #{key_index + 1} 사용")

        try:
            client = genai.Client(api_key=api_key)

            # 모든 이미지와 프롬프트를 하나의 요청으로
            parts = image_parts + [{"text": prompt}]

            print("Gemini API 호출 중... (이미지 분석에 시간이 소요됩니다)")

            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=[
                    {
                        "role": "user",
                        "parts": parts
                    }
                ]
            )

            print("응답 수신 완료. 파싱 중...")

            # 응답 파싱
            result = parse_json_response(response.text)

            if result and "results" in result:
                analysis_results = result["results"]
                analysis_time = datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S")

                # 캡처 시각 및 분석 시각 추가
                for i, item in enumerate(analysis_results):
                    # 시그널 검증
                    if item.get("signal") not in SIGNAL_CATEGORIES:
                        item["signal"] = "중립"

                    # 매칭되는 종목의 캡처 시각 추가
                    matched_stock = next(
                        (s for s in valid_stocks if s["code"] == item.get("code")),
                        None
                    )
                    if matched_stock:
                        item["capture_time"] = matched_stock.get("capture_time", "N/A")
                    else:
                        item["capture_time"] = "N/A"

                    item["analysis_time"] = analysis_time

                print(f"\n분석 완료: {len(analysis_results)}개 종목")
                rotate_to_next_key()
                return analysis_results

            print("[WARNING] 응답 파싱 실패. 재시도...")

        except Exception as e:
            error_msg = str(e)
            print(f"  [KEY #{key_index + 1}] 오류: {error_msg[:100]}")

            if "429" in error_msg or "quota" in error_msg.lower() or "rate" in error_msg.lower():
                mark_key_failed(key_index)
                rotate_to_next_key()
                time.sleep(2)
                continue

            if "404" in error_msg:
                print("[ERROR] 모델을 찾을 수 없습니다.")
                return []

            rotate_to_next_key()
            time.sleep(1)

    print(f"[ERROR] {max_retries}회 시도 후 실패")
    return []


# 하위 호환성을 위한 별칭
def analyze_stocks(scrape_results: list[dict], capture_dir: Path) -> list[dict]:
    """analyze_stocks_batch의 별칭 (하위 호환성)"""
    return analyze_stocks_batch(scrape_results, capture_dir)


# KIS API 데이터 분석용 프롬프트
KIS_ANALYSIS_PROMPT = """당신은 20년 경력의 대한민국 주식 시장 전문 퀀트 애널리스트입니다.

아래에 한국투자증권 OpenAPI에서 수집한 {count}개 종목의 실시간 데이터가 JSON 형식으로 제공됩니다.

## 데이터 설명
각 종목에는 다음 정보가 포함되어 있습니다:
- **ranking**: 거래량 순위 및 거래량 변화율
- **price**: 현재가, 등락률, 시고저종, 52주 고저
- **valuation**: PER, PBR, EPS, BPS
- **investor_flow**: 외인/기관/개인 순매수 동향 (당일, 5일)
- **foreign_institution**: 외인/기관 5일/20일 누적 순매수
- **member_trading**: 주요 증권사 매매 동향
- **price_history**: 최근 20거래일 일봉 데이터
- **order_book**: 호가 정보 (매수/매도 잔량)

## 분석 요청
각 종목에 대해 다음을 수행하세요:

1. **기술적 분석**: 가격 추세, 거래량 변화, 이동평균 대비 위치 등 제공된 모든 데이터, 지표, 수치 기반 분석
2. **수급 분석**: 외인/기관 매매 동향, 프로그램 매매 흐름
3. **밸류에이션 분석**: PER/PBR 수준 및 업종 대비 적정성
4. **시그널 결정**: [적극매수, 매수, 중립, 매도, 적극매도] 중 하나 선택
5. **분석 근거**: 시그널 결정의 핵심 근거를 2~3문장으로 설명

## 분석 대상 종목 데이터
```json
{stock_data}
```

반드시 아래 JSON 형식으로만 응답하세요. 다른 텍스트 없이 JSON만 출력하세요:
```json
{{
  "analysis_time": "분석 시각 (YYYY-MM-DD HH:MM:SS)",
  "results": [
    {{
      "code": "종목코드",
      "name": "종목명",
      "market": "KOSPI/KOSDAQ",
      "current_price": 현재가(숫자),
      "change_rate": 등락률(숫자),
      "signal": "시그널",
      "reason": "분석 근거 (2~3문장)",
      "key_factors": {{
        "price_trend": "가격 추세 (상승/횡보/하락)",
        "volume_signal": "거래량 시그널 (급증/증가/보통/감소)",
        "foreign_flow": "외인 동향 (매수우위/중립/매도우위)",
        "institution_flow": "기관 동향 (매수우위/중립/매도우위)",
        "valuation": "밸류에이션 (저평가/적정/고평가)"
      }},
      "risk_level": "위험도 (높음/중간/낮음)",
      "confidence": 신뢰도(0.0~1.0)
    }}
  ]
}}
```

중요: 모든 {count}개 종목에 대해 분석 결과를 반드시 포함해야 합니다.
"""


def analyze_kis_data(
    stocks_data: dict,
    stock_codes: list[str] | None = None,
    max_retries: int = 3
) -> list[dict]:
    """KIS API 데이터 기반 종목 분석

    Args:
        stocks_data: 변환된 KIS 데이터 (top50_gemini.json 형식)
        stock_codes: 분석할 종목 코드 리스트 (없으면 전체)
        max_retries: 최대 재시도 횟수

    Returns:
        분석 결과 리스트
    """
    import json

    print("\n=== KIS API 데이터 AI 분석 ===\n")
    print(f"사용 가능한 API 키: {len(GEMINI_API_KEYS)}개")

    stocks = stocks_data.get("stocks", {})

    # 분석 대상 종목 필터링
    if stock_codes:
        target_stocks = {code: stocks[code] for code in stock_codes if code in stocks}
    else:
        target_stocks = stocks

    if not target_stocks:
        print("[ERROR] 분석할 종목이 없습니다.")
        return []

    print(f"분석 대상: {len(target_stocks)}개 종목\n")

    # 프롬프트 생성
    prompt = KIS_ANALYSIS_PROMPT.format(
        count=len(target_stocks),
        stock_data=json.dumps(target_stocks, ensure_ascii=False, indent=2)
    )

    # API 호출 시도
    for attempt in range(max_retries):
        key_info = get_next_api_key()
        if not key_info:
            print("[ERROR] 사용 가능한 API 키가 없습니다.")
            return []

        api_key, key_index = key_info
        print(f"[시도 {attempt + 1}/{max_retries}] API 키 #{key_index + 1} 사용")

        try:
            client = genai.Client(api_key=api_key)

            print("Gemini API 호출 중... (데이터 분석에 시간이 소요됩니다)")

            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=[
                    {
                        "role": "user",
                        "parts": [{"text": prompt}]
                    }
                ]
            )

            print("응답 수신 완료. 파싱 중...")

            # 응답 파싱
            result = parse_json_response(response.text)

            if result and "results" in result:
                analysis_results = result["results"]
                analysis_time = result.get(
                    "analysis_time",
                    datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S")
                )

                # 시그널 검증 및 메타데이터 추가
                for item in analysis_results:
                    if item.get("signal") not in SIGNAL_CATEGORIES:
                        item["signal"] = "중립"
                    item["analysis_time"] = analysis_time
                    item["data_source"] = "KIS_API"

                print(f"\n분석 완료: {len(analysis_results)}개 종목")
                rotate_to_next_key()
                return analysis_results

            print("[WARNING] 응답 파싱 실패. 재시도...")

        except Exception as e:
            error_msg = str(e)
            print(f"  [KEY #{key_index + 1}] 오류: {error_msg[:100]}")

            if "429" in error_msg or "quota" in error_msg.lower() or "rate" in error_msg.lower():
                mark_key_failed(key_index)
                rotate_to_next_key()
                time.sleep(2)
                continue

            if "404" in error_msg:
                print("[ERROR] 모델을 찾을 수 없습니다.")
                return []

            rotate_to_next_key()
            time.sleep(1)

    print(f"[ERROR] {max_retries}회 시도 후 실패")
    return []


def analyze_kis_data_batch(
    stocks_data: dict,
    batch_size: int = 10,
    max_retries: int = 3
) -> list[dict]:
    """KIS API 데이터 배치 분석 (대량 종목용)

    Args:
        stocks_data: 변환된 KIS 데이터
        batch_size: 배치당 종목 수
        max_retries: 최대 재시도 횟수

    Returns:
        전체 분석 결과 리스트
    """
    stocks = stocks_data.get("stocks", {})
    all_codes = list(stocks.keys())

    print(f"\n=== KIS 데이터 배치 분석 시작 ===")
    print(f"총 종목: {len(all_codes)}개, 배치 크기: {batch_size}개\n")

    all_results = []

    for i in range(0, len(all_codes), batch_size):
        batch_codes = all_codes[i:i + batch_size]
        batch_num = i // batch_size + 1
        total_batches = (len(all_codes) + batch_size - 1) // batch_size

        print(f"\n--- 배치 {batch_num}/{total_batches} ---")

        results = analyze_kis_data(
            stocks_data,
            stock_codes=batch_codes,
            max_retries=max_retries
        )

        if results:
            all_results.extend(results)
            print(f"배치 {batch_num} 완료: {len(results)}개 종목 분석")
        else:
            print(f"배치 {batch_num} 실패")

        # 배치 간 딜레이 (rate limit 방지)
        if i + batch_size < len(all_codes):
            print("다음 배치 대기 중... (3초)")
            time.sleep(3)

    print(f"\n=== 배치 분석 완료 ===")
    print(f"총 분석 완료: {len(all_results)}개 종목")

    return all_results
