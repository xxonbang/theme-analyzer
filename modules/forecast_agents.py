"""Multi-Agent 예측 모듈

3개 에이전트(뉴스/감성, 시장데이터, 종합) + 2-Phase JSON 구조화.
예측당 총 6회 API 호출 (1 + 1 + 3 voting + 1 JSON).
"""
import time
import requests
from typing import Dict, List, Optional

from modules.theme_forecast import (
    GEMINI_API_URL,
    _extract_text_from_response,
    _call_gemini_phase2,
    _self_consistency_vote,
)
from modules.utils import KST
from datetime import datetime


def _call_agent(prompt: str, api_key: str, use_search: bool = False) -> Optional[str]:
    """에이전트 API 호출 (텍스트 반환)"""
    url = f"{GEMINI_API_URL}?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.5,
            "thinkingConfig": {"thinkingBudget": -1},
        },
    }
    if use_search:
        payload["tools"] = [{"google_search": {}}]

    resp = requests.post(url, json=payload, timeout=180)
    resp.raise_for_status()

    text = _extract_text_from_response(resp.json())
    return text.strip() if text.strip() else None


def agent_news_sentiment(context: str, api_key: str) -> Optional[str]:
    """에이전트 1: 뉴스/감성 분석 (Google Search 사용)"""
    today = datetime.now(KST).strftime("%Y년 %m월 %d일")
    today_search = datetime.now(KST).strftime("%m월 %d일")

    prompt = f"""당신은 한국 주식시장 뉴스/감성 분석 전문가입니다.
오늘은 {today}이며, 장 개장 전 기준입니다.

### 임무
Google Search를 통해 최신 뉴스를 수집하고, 한국 주식시장 테마에 미치는 영향을 분석하세요.

### Google Search 지시 — 정확히 3건만 검색하세요

**검색 1: "미국 증시 마감 {today_search}"**
- 실제로 크게 움직인 섹터/종목과 원인(촉매)을 파악
- 한국 시장 테마로의 인과관계를 도출

**검색 2: "한국 증시 전망 {today_search}"**
- 증권사 리포트/뉴스에서 구체적 테마 키워드 추출
- 전일 테마와의 연속성 또는 신규성 판단

**검색 3: "한국 경제 일정 이번주"**
- 향후 1개월 내 주요 이벤트와 테마 연결

### 시장 심리 데이터
아래 데이터에서 시장 심리 지표(Fear & Greed 등)가 있다면 해석에 반영하세요.

{context}

### 출력
각 촉매별로:
- 뉴스/이벤트 요약
- 영향받는 테마명
- 인과관계 설명
- 신뢰도 판단 (높음/보통/낮음)
JSON 형식 불필요. 상세한 텍스트 분석을 출력하세요."""

    return _call_agent(prompt, api_key, use_search=True)


def agent_market_data(context: str, api_key: str) -> Optional[str]:
    """에이전트 2: 시장 데이터 분석 (Google Search 없음, 컨텍스트만 활용)"""
    prompt = f"""당신은 한국 주식시장 정량 데이터 분석 전문가입니다.

### 임무
아래 시장 데이터만을 활용하여 테마 분석을 수행하세요.
Google Search는 사용하지 마세요.

### 분석 항목
1. **거래대금/수급 패턴**: 전일 거래대금 상위 종목의 수급 흐름 분석
2. **US 시장 연관성**: 미국 시장 정량 데이터와 한국 테마의 상관관계
3. **테마 모멘텀**: 모멘텀 점수 해석 및 지속 가능성 판단
4. **섹터 로테이션**: 로테이션 신호 해석 (있는 경우)

### 시장 데이터
{context}

### 출력
각 테마별로:
- 데이터 기반 근거 (거래대금, 수급, 모멘텀)
- 지속 가능성 판단
- 대장주 후보 (종목명, 종목코드, 데이터 근거)
JSON 형식 불필요. 정량 데이터 기반 텍스트 분석을 출력하세요."""

    return _call_agent(prompt, api_key, use_search=False)


def _build_synthesis_prompt(news_analysis: str, market_analysis: str, context: str) -> str:
    """종합 에이전트 프롬프트"""
    today = datetime.now(KST).strftime("%Y년 %m월 %d일")

    return f"""당신은 한국 주식시장 테마 예측 종합 판단 전문가입니다.
오늘은 {today}이며, 장 개장 전 기준입니다.

### 임무
두 전문가의 분석 결과를 종합하여 최종 테마 예측을 도출하세요.

### 에이전트 1 분석 (뉴스/감성)
{news_analysis}

### 에이전트 2 분석 (시장 데이터)
{market_analysis}

### 원본 시장 데이터
{context}

### 분석 방법론 — 반드시 아래 순서대로 추론하세요
1단계 [교차 검증]: 두 에이전트가 공통으로 언급한 테마를 우선 채택
2단계 [보완 분석]: 한쪽만 언급했지만 근거가 강한 테마를 추가 검토
3단계 [데이터 확인]: 실제 거래대금/수급 데이터가 뒷받침하는지 재확인
4단계 [신뢰도 판정]: 촉매 강도 + 데이터 뒷받침 + 에이전트 합의도로 신뢰도 부여
5단계 [최종 정리]: 오늘/단기/장기로 분류하여 상세 텍스트로 정리

### 대장주 선정 규칙
- 각 테마당 최대 3개 종목
- priority 1: 거래대금 최상위 + 외국인/기관 동반 순매수
- priority 2: 거래대금 상위 + 수급 부분 충족
- priority 3: 테마 대표성 높으나 데이터 미흡

### 출력
오늘/단기/장기 각 카테고리별로:
- 테마명, 핵심 촉매, 신뢰도(높음/보통/낮음)
- 대장주 후보 (종목명, 종목코드, 선정 근거)
JSON 형식 불필요. 상세한 종합 분석 텍스트를 출력하세요."""


def run_multi_agent_forecast(context: str, api_keys: List[str]) -> Optional[Dict]:
    """Multi-Agent 오케스트레이터

    1. agent_news_sentiment (1회, Google Search)
    2. agent_market_data (1회, 검색 없음)
    3. agent_synthesize (3회 voting, Google Search)
    4. _call_gemini_phase2 (1회, JSON 구조화)
    총 6회 API 호출
    """
    if not api_keys:
        return None

    api_key = api_keys[0]  # 단일 키 사용, 나머지는 retry 보존

    # Step 1: 뉴스/감성 에이전트
    print("    Agent 1: 뉴스/감성 분석...")
    news_analysis = agent_news_sentiment(context, api_key)
    if not news_analysis:
        print("    ⚠ Agent 1 실패")
        return None

    time.sleep(1)

    # Step 2: 시장 데이터 에이전트
    print("    Agent 2: 시장 데이터 분석...")
    market_analysis = agent_market_data(context, api_key)
    if not market_analysis:
        print("    ⚠ Agent 2 실패")
        return None

    time.sleep(1)

    # Step 3: 종합 에이전트 (Self-Consistency 3회)
    print("    Agent 3: 종합 판단 (Self-Consistency 3회)...")
    synthesis_prompt = _build_synthesis_prompt(news_analysis, market_analysis, context)
    reasoning = _self_consistency_vote(synthesis_prompt, api_key, n_samples=3)
    if not reasoning:
        print("    ⚠ Agent 3 실패")
        return None

    time.sleep(1)

    # Step 4: JSON 구조화 (Phase 2)
    print("    Phase 2: JSON 구조화...")
    result = _call_gemini_phase2(reasoning, api_key)
    if not result:
        # retry with failover key
        for fallback_key in api_keys[1:]:
            try:
                result = _call_gemini_phase2(reasoning, fallback_key)
                if result:
                    break
            except Exception:
                continue

    return result
