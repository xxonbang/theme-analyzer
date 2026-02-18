# Multi-Criteria Stock Evaluation & Visual Indicator System

종목 선정 기준 평가 및 시각적 인디케이터 시스템 기술 명세서

---

## 목차

1. [시스템 개요](#1-시스템-개요)
2. [평가 기준 상세 (7개)](#2-평가-기준-상세-7개)
3. [데이터 구조](#3-데이터-구조)
4. [프론트엔드 시각화 명세](#4-프론트엔드-시각화-명세)
5. [CSS 애니메이션 명세](#5-css-애니메이션-명세)
6. [백엔드-프론트엔드 데이터 흐름](#6-백엔드-프론트엔드-데이터-흐름)

---

## 1. 시스템 개요

### 1.1 목적

한국 주식 시장의 개별 종목을 **7개 독립적인 기준**으로 평가하고, 각 기준의 충족 여부를 프론트엔드에서 **색상 코딩된 시각적 인디케이터**로 표시하는 시스템이다.

### 1.2 핵심 특징

- **7개 평가 기준**: 전고점 돌파, 모멘텀 이력(끼), 심리적 저항선 돌파, 이동평균선 정배열, 외국인/기관 수급, 프로그램 매매, 거래대금 TOP30
- **Admin 전용 기능**: 인디케이터는 관리자 권한이 있는 사용자에게만 표시
- **반응형 디자인**: 모바일에서는 색상 도트, PC/태블릿에서는 뱃지 형태로 표시
- **전체 충족 효과**: 7개 기준 모두 충족 시 금색 하이라이트 및 애니메이션 적용
- **판정 근거 제공**: 각 인디케이터 클릭 시 해당 기준의 구체적 판정 근거 표시

### 1.3 적용 범위

| 항목 | 설명 |
|------|------|
| 대상 시장 | 한국 주식 시장 (KOSPI, KOSDAQ) |
| 평가 주기 | 장중 또는 장 마감 후 일 1회 이상 |
| 표시 대상 | 시스템이 추적하는 모든 종목 |
| 접근 권한 | Admin 사용자만 인디케이터 확인 가능 |

---

## 2. 평가 기준 상세 (7개)

각 기준은 독립적으로 평가되며, 결과는 `met` (충족 여부), `reason` (판정 근거), 그리고 기준별 추가 필드로 구성된다.

---

### 2.1 전고점 돌파 (빨간색)

**정의**: 현재 주가가 과거 일정 기간의 최고가를 돌파했는지 판단한다. 6개월(약 120영업일) 일봉 최고가 돌파와 52주 신고가 돌파를 구분하여 판정한다.

#### 필요 입력 데이터

| 데이터 | 설명 | 비고 |
|--------|------|------|
| `current_price` | 현재가 (정수, 원) | 실시간 또는 종가 기준 |
| `daily_prices` | 최소 120영업일 일봉 데이터 (최신순 정렬) | 각 일봉에 `고가(high)` 필드 필수 |
| `w52_high` | 52주 최고가 (정수, 원) | 외부 API 또는 별도 계산 |

#### 평가 로직

```
function check_high_breakout(current_price, daily_prices, w52_high):
    result = { met: false, is_52w_high: false, reason: null }

    if current_price is empty:
        return result

    # Step 1: 6개월(120영업일) 최고가 계산
    highs = [각 일봉의 고가 for 최근 120영업일 일봉]
    six_month_high = max(highs)

    if current_price >= six_month_high:
        result.met = true
        result.reason = "6개월 최고가 {six_month_high}원 돌파 (현재가 {current_price}원)"

    # Step 2: 52주 신고가 판정
    if w52_high exists AND current_price >= w52_high:
        result.met = true
        result.is_52w_high = true
        result.reason = "52주 신고가 경신 (기존 {w52_high}원 -> 현재 {current_price}원)"

    return result
```

#### 출력 형식

```json
{
  "met": true,
  "is_52w_high": true,
  "reason": "52주 신고가 경신 (기존 45,000원 -> 현재 47,200원)"
}
```

#### 특수 규칙

- `is_52w_high`가 `true`이면 프론트엔드에서 **빨간 인디케이터 2개** 표시 (모바일: 도트 2개, PC: "52주 신고가" 뱃지)
- 52주 신고가는 6개월 고점 돌파를 포함하므로, 52주 판정 시 reason을 52주 기준으로 덮어쓴다

---

### 2.2 끼 보유 (주황색)

**정의**: 해당 종목이 과거에 강한 상승 모멘텀(상한가 달성, 15% 이상 급등)을 보인 이력이 있는지 판단한다. "끼"란 향후에도 강한 움직임을 보일 잠재력을 의미한다.

#### 필요 입력 데이터

| 데이터 | 설명 | 비고 |
|--------|------|------|
| `daily_prices` | 일봉 데이터 (최신순 정렬) | 충분한 과거 기간 (최소 120일 이상 권장) |
| 각 일봉의 등락률 또는 종가/기준가 | 등락률 계산 가능한 데이터 | 등락률 직접 제공 또는 (종가 - 기준가) / 기준가 로 계산 |
| 각 일봉의 날짜 | 표시용 | `YYYYMMDD` 형식 |

#### 평가 로직

```
function check_momentum_history(daily_prices):
    result = { met: false, had_limit_up: false, had_15pct_rise: false, reason: null }

    if daily_prices is empty:
        return result

    reasons = []

    for each price_data in daily_prices:
        # 등락률 계산: (종가 - 기준가) / 기준가 * 100
        change_rate = calculate_change_rate(price_data)

        if change_rate is null:
            continue

        date = format_date(price_data.date)

        # 상한가 판정 (등락률 >= 29%)
        if change_rate >= 29.0 AND NOT result.had_limit_up:
            result.had_limit_up = true
            result.met = true
            reasons.append("상한가 기록 ({date}, +{change_rate}%)")

        # 15% 이상 급등 판정 (종가 기준)
        if change_rate >= 15.0 AND NOT result.had_15pct_rise:
            result.had_15pct_rise = true
            result.met = true
            reasons.append("+15% 이상 상승 유지 ({date}, +{change_rate}%)")

        # 두 조건 모두 발견하면 조기 종료
        if result.had_limit_up AND result.had_15pct_rise:
            break

    if reasons is not empty:
        result.reason = join(reasons, " | ")

    return result
```

#### 출력 형식

```json
{
  "met": true,
  "had_limit_up": true,
  "had_15pct_rise": true,
  "reason": "상한가 기록 (2025-11-05, +29.8%) | +15% 이상 상승 유지 (2025-12-12, +17.3%)"
}
```

#### 보충 설명

- 상한가 기준은 한국 주식 시장의 가격 제한폭(일반적으로 +30%)에 근거하며, 실제 등락률 29% 이상을 상한가로 간주한다
- 등락률은 종가 기준이므로 "시장 종료 시점까지 유지된" 상승폭을 의미한다
- 두 조건(상한가, 15% 급등)은 OR 관계: 둘 중 하나만 충족해도 `met = true`

---

### 2.3 심리적 저항선 돌파 (노랑색)

**정의**: 현재가가 호가 단위 변경 구간 또는 심리적 라운드 넘버를 돌파했는지 판단한다. 트레이더들이 심리적으로 인식하는 가격 저항 수준의 돌파를 감지한다.

#### 필요 입력 데이터

| 데이터 | 설명 | 비고 |
|--------|------|------|
| `current_price` | 현재가 (정수, 원) | |
| `prev_close` | 전일 종가 (정수, 원) | `현재가 - 전일대비` 로 계산 가능 |

#### 조건 A: 호가 단위 변경 구간 돌파 (OR)

한국 주식 시장의 호가 단위는 가격대에 따라 달라진다. 이 경계를 넘는 것은 심리적 저항선 돌파를 의미한다.

**호가 단위 경계값 (boundaries)**:

| 경계값 | 의미 |
|--------|------|
| 2,000원 | 호가 단위 1원 -> 5원 변경 |
| 5,000원 | 호가 단위 5원 -> 10원 변경 |
| 20,000원 | 호가 단위 10원 -> 50원 변경 |
| 50,000원 | 호가 단위 50원 -> 100원 변경 |
| 200,000원 | 호가 단위 100원 -> 500원 변경 |
| 500,000원 | 호가 단위 500원 -> 1,000원 변경 |

**판정 로직**:
- **돌파**: `전일종가 < boundary <= 현재가`
- **돌파 직전**: `전일종가 < boundary` AND `현재가 < boundary` AND `(boundary - 현재가) / boundary * 100 <= 3%`

#### 조건 B: 라운드 넘버 돌파 (OR)

가격대에 따라 트레이더가 의식하는 "딱 떨어지는 숫자" 기준이 다르다.

**가격대별 라운드 넘버 단위**:

| 현재 가격대 | 라운드 단위 | 예시 |
|------------|-----------|------|
| 50만원 이상 | 10만원 단위 | 500,000 / 600,000 / 700,000... |
| 10만원 이상 | 5만원 단위 | 100,000 / 150,000 / 200,000... |
| 5만원 이상 | 1만원 단위 | 50,000 / 60,000 / 70,000... |
| 2만원 이상 | 5천원 단위 | 20,000 / 25,000 / 30,000... |
| 1만원 이상 | 1천원 단위 | 10,000 / 11,000 / 12,000... |
| 5천원 이상 | 500원 단위 | 5,000 / 5,500 / 6,000... |
| 1천원 이상 | 100원 단위 | 1,000 / 1,100 / 1,200... |

**판정 로직**: `전일종가 < round_number <= 현재가`

#### 평가 로직

```
TICK_BOUNDARIES = [2000, 5000, 20000, 50000, 200000, 500000]

ROUND_LEVELS = [
    (500000, 100000),  # 50만 이상: 10만 단위
    (100000, 50000),   # 10만 이상: 5만 단위
    (50000,  10000),   # 5만 이상: 1만 단위
    (20000,  5000),    # 2만 이상: 5천 단위
    (10000,  1000),    # 1만 이상: 1천 단위
    (5000,   500),     # 5천 이상: 500 단위
    (1000,   100),     # 1천 이상: 100 단위
]

function check_resistance_breakout(current_price, prev_close):
    result = { met: false, reason: null }

    if current_price is empty:
        return result

    reasons = []

    # 조건 A: 호가 단위 경계 돌파
    if prev_close exists:
        for boundary in TICK_BOUNDARIES:
            if prev_close < boundary <= current_price:
                reasons.append("호가 단위 변경 구간 {boundary}원 돌파")
                break
            if prev_close < boundary AND current_price < boundary:
                proximity_pct = (boundary - current_price) / boundary * 100
                if proximity_pct <= 3:
                    reasons.append("호가 단위 변경 구간 {boundary}원 돌파 직전 ({proximity_pct}% 남음)")
                    break

    # 조건 B: 라운드 넘버 돌파
    if prev_close exists:
        for (threshold, unit) in ROUND_LEVELS:
            if current_price >= threshold:
                # 전일 종가 바로 위의 라운드 넘버 계산
                next_round = floor(prev_close / unit + 1) * unit
                if prev_close < next_round <= current_price:
                    reasons.append("심리적 저항선 {next_round}원 돌파")
                break  # 가격대별로 하나만 적용

    if reasons is not empty:
        result.met = true
        result.reason = join(reasons, " | ")

    return result
```

#### 출력 형식

```json
{
  "met": true,
  "reason": "호가 단위 변경 구간 50,000원 돌파 | 심리적 저항선 50,000원 돌파"
}
```

#### 보충 설명

- 조건 A와 B는 OR 관계: 둘 중 하나만 충족해도 `met = true`
- 호가 단위 경계 돌파와 라운드 넘버 돌파가 동시에 발생할 수 있으며, 이 경우 두 이유가 모두 reason에 포함된다
- 라운드 넘버 판정은 현재가의 가격대에 해당하는 단위만 적용한다 (상위 가격대 우선)

---

### 2.4 이동평균선 정배열 (청록색)

**정의**: 현재가와 5개 이동평균선(MA5, MA10, MA20, MA60, MA120)이 완전한 정배열을 이루는지 판단한다. 정배열은 강한 상승 추세를 의미한다.

#### 필요 입력 데이터

| 데이터 | 설명 | 비고 |
|--------|------|------|
| `current_price` | 현재가 (정수, 원) | |
| `daily_prices` | **최소 120영업일** 이상 종가 데이터 (최신순 정렬) | 각 일봉에 `종가(close)` 필드 필수 |

#### 이동평균 계산

**SMA (Simple Moving Average)** 방식을 사용한다.

```
function calc_sma(closes, period):
    if len(closes) < period:
        return null
    return sum(closes[0:period]) / period
```

| 이동평균 | 기간 | 의미 |
|---------|------|------|
| MA5 | 5일 | 초단기 추세 |
| MA10 | 10일 | 단기 추세 |
| MA20 | 20일 | 중단기 추세 (약 1개월) |
| MA60 | 60일 | 중기 추세 (약 3개월) |
| MA120 | 120일 | 장기 추세 (약 6개월) |

#### 정배열 조건

```
현재가 > MA5 > MA10 > MA20 > MA60 > MA120
```

모든 비교에서 **엄격한 부등호(>)** 를 사용한다. 등호(=)는 정배열로 인정하지 않는다.

#### 평가 로직

```
function check_ma_alignment(current_price, daily_prices):
    result = { met: false, ma_values: {}, reason: null }

    if current_price is empty OR daily_prices is empty:
        return result

    # 종가 배열 추출 (최신순)
    closes = [각 일봉의 종가 for daily_prices]

    periods = [5, 10, 20, 60, 120]
    ma_values = {}
    for period in periods:
        ma = calc_sma(closes, period)
        if ma is not null:
            ma_values["MA{period}"] = round(ma)

    result.ma_values = ma_values

    # 모든 MA가 계산 가능한지 확인
    if len(ma_values) < len(periods):
        result.reason = "이동평균 계산 불가 (데이터 부족: {len(closes)}일분)"
        return result

    # 정배열 판정
    values = [current_price, MA5, MA10, MA20, MA60, MA120]
    is_aligned = all(values[i] > values[i+1] for i in range(len(values)-1))

    if is_aligned:
        result.met = true
        result.reason = "현재가({current_price}) > MA5({MA5}) > MA10({MA10}) > MA20({MA20}) > MA60({MA60}) > MA120({MA120}) 정배열"
    else:
        result.reason = "정배열 미충족 (MA5:{MA5} | MA10:{MA10} | MA20:{MA20} | MA60:{MA60} | MA120:{MA120})"

    return result
```

#### 출력 형식

```json
{
  "met": true,
  "ma_values": {
    "MA5": 48500,
    "MA10": 47200,
    "MA20": 45800,
    "MA60": 42100,
    "MA120": 39500
  },
  "reason": "현재가(49,200) > MA5(48,500) > MA10(47,200) > MA20(45,800) > MA60(42,100) > MA120(39,500) 정배열"
}
```

---

### 2.5 외국인/기관 수급 (파란색)

**정의**: 당일 외국인과 기관이 **동시에** 순매수하고 있는지 판단한다. 두 주체가 동시에 매수한다는 것은 해당 종목에 대한 강한 수급 신호를 의미한다.

#### 필요 입력 데이터

| 데이터 | 설명 | 비고 |
|--------|------|------|
| `foreign_net` | 외국인 순매수 수량 (정수, 주) | 양수 = 순매수, 음수 = 순매도 |
| `institution_net` | 기관 순매수 수량 (정수, 주) | 양수 = 순매수, 음수 = 순매도 |

#### 평가 로직

```
function check_supply_demand(foreign_net, institution_net):
    result = { met: false, reason: null }

    # 핵심 조건: 외국인 AND 기관 동시 순매수
    if foreign_net > 0 AND institution_net > 0:
        result.met = true

    # reason 구성 (충족 여부와 무관하게 수급 현황 표시)
    parts = []
    if foreign_net:
        sign = "+" if foreign_net > 0 else ""
        parts.append("외국인 {sign}{foreign_net}주")
    if institution_net:
        sign = "+" if institution_net > 0 else ""
        parts.append("기관 {sign}{institution_net}주")

    if parts is not empty:
        result.reason = join(parts, " | ")

    return result
```

#### 출력 형식

```json
{
  "met": true,
  "reason": "외국인 +125,340주 | 기관 +58,200주"
}
```

#### 보충 설명

- **AND 조건**: 외국인만 순매수하거나, 기관만 순매수하는 경우에는 `met = false`
- `reason`은 충족 여부와 무관하게 현재 수급 현황을 항상 표시한다 (미충족 시에도 참고 정보로 제공)

---

### 2.6 프로그램 매매 (보라색)

**정의**: 해당 종목에 프로그램 매매 순매수가 유입되고 있는지 판단한다.

#### 필요 입력 데이터

| 데이터 | 설명 | 비고 |
|--------|------|------|
| `program_net_buy_qty` | 프로그램 순매수 수량 (정수, 주) | 양수 = 순매수, 음수 = 순매도 |

#### 평가 로직

```
function check_program_trading(program_net_buy_qty):
    result = { met: false, reason: null }

    qty = program_net_buy_qty or 0

    if qty > 0:
        result.met = true
        result.reason = "프로그램 순매수 +{qty}주"
    elif qty < 0:
        result.reason = "프로그램 순매도 {qty}주"

    return result
```

#### 출력 형식

```json
{
  "met": true,
  "reason": "프로그램 순매수 +32,100주"
}
```

---

### 2.7 거래대금 TOP30 (자홍색)

**정의**: 해당 종목이 당일 거래대금 기준 상위 30위 이내에 포함되는지 판단한다. 높은 거래대금은 시장의 관심과 유동성을 의미한다.

#### 필요 입력 데이터

| 데이터 | 설명 | 비고 |
|--------|------|------|
| `stock_code` | 평가 대상 종목 코드 | |
| `top30_codes` | 당일 거래대금 TOP30 종목 코드 집합 | KOSPI/KOSDAQ 통합 또는 개별 시장 기준 |

#### 평가 로직

```
function check_top30_trading_value(stock_code, top30_codes):
    result = { met: false, reason: null }

    if stock_code in top30_codes:
        result.met = true
        result.reason = "당일 거래대금 TOP30 포함"

    return result
```

#### 출력 형식

```json
{
  "met": true,
  "reason": "당일 거래대금 TOP30 포함"
}
```

#### 보충 설명

- TOP30 집합 구성 시, KOSPI와 KOSDAQ 각각의 TOP30을 합산하여 사용할 수 있다 (최대 60개 종목)
- 또는 전체 시장 통합 TOP30으로 구성할 수도 있다 (구현 시 선택)

---

## 3. 데이터 구조

### 3.1 Input 데이터 명세

#### 종목 기본 정보

```json
{
  "code": "005930",
  "name": "삼성전자",
  "current_price": 72400,
  "change_price": 1200
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `code` | string | O | 종목 코드 (6자리) |
| `name` | string | O | 종목명 |
| `current_price` | integer | O | 현재가 (원) |
| `change_price` | integer | O | 전일 대비 등락 금액 (원), 전일종가 = current_price - change_price |

#### 일봉 데이터 (최신순 정렬)

```json
[
  {
    "date": "20260218",
    "open": 71800,
    "high": 72900,
    "low": 71500,
    "close": 72400,
    "volume": 12345678,
    "base_price": 71200,
    "change_rate": 1.69
  }
]
```

| 필드 | 타입 | 필수 | 설명 | 사용 기준 |
|------|------|------|------|----------|
| `date` | string | O | 날짜 (YYYYMMDD) | 2.2 |
| `high` | integer | O | 고가 (원) | 2.1 |
| `close` | integer | O | 종가 (원) | 2.4 |
| `base_price` | integer | - | 기준가/전일종가 (원) | 2.2 (등락률 계산) |
| `change_rate` | float | - | 등락률 (%) | 2.2 (직접 제공 시) |

**최소 데이터 수량**: 120영업일 (MA120 계산에 필요)

#### 펀더멘탈 데이터

```json
{
  "w52_high": 73200,
  "program_net_buy_qty": 32100
}
```

| 필드 | 타입 | 필수 | 설명 | 사용 기준 |
|------|------|------|------|----------|
| `w52_high` | integer | - | 52주 최고가 (원) | 2.1 |
| `program_net_buy_qty` | integer | - | 프로그램 순매수 수량 (주) | 2.6 |

#### 투자자 수급 데이터

```json
{
  "foreign_net": 125340,
  "institution_net": 58200
}
```

| 필드 | 타입 | 필수 | 설명 | 사용 기준 |
|------|------|------|------|----------|
| `foreign_net` | integer | O | 외국인 순매수 (주) | 2.5 |
| `institution_net` | integer | O | 기관 순매수 (주) | 2.5 |

#### 거래대금 TOP30 데이터

종목 코드의 집합(Set)으로 제공한다.

```json
["005930", "000660", "035420", "..."]
```

---

### 3.2 Output: Criteria Result 구조

#### 단일 기준 결과 (CriterionResult)

```json
{
  "met": true,
  "reason": "판정 근거 텍스트",
  "...extra_fields": "기준별 추가 필드"
}
```

**기준별 추가 필드**:

| 기준 | 추가 필드 | 타입 | 설명 |
|------|----------|------|------|
| 전고점 돌파 | `is_52w_high` | boolean | 52주 신고가 여부 |
| 끼 보유 | `had_limit_up` | boolean | 상한가 이력 여부 |
| 끼 보유 | `had_15pct_rise` | boolean | 15% 이상 급등 이력 |
| 정배열 | `ma_values` | object | 각 MA값 (`{ "MA5": 48500, ... }`) |

#### 종목별 전체 평가 결과 (StockCriteria)

```json
{
  "high_breakout": {
    "met": true,
    "is_52w_high": false,
    "reason": "6개월 최고가 45,000원 돌파 (현재가 47,200원)"
  },
  "momentum_history": {
    "met": true,
    "had_limit_up": false,
    "had_15pct_rise": true,
    "reason": "+15% 이상 상승 유지 (2025-11-15, +16.2%)"
  },
  "resistance_breakout": {
    "met": false,
    "reason": null
  },
  "ma_alignment": {
    "met": true,
    "ma_values": { "MA5": 46800, "MA10": 45900, "MA20": 44200, "MA60": 41500, "MA120": 38900 },
    "reason": "현재가(47,200) > MA5(46,800) > ... 정배열"
  },
  "supply_demand": {
    "met": true,
    "reason": "외국인 +125,340주 | 기관 +58,200주"
  },
  "program_trading": {
    "met": false,
    "reason": "프로그램 순매도 -12,500주"
  },
  "top30_trading_value": {
    "met": true,
    "reason": "당일 거래대금 TOP30 포함"
  },
  "all_met": false
}
```

#### 전체 종목 평가 결과

```json
{
  "005930": { "high_breakout": { ... }, "momentum_history": { ... }, ..., "all_met": false },
  "000660": { "high_breakout": { ... }, "momentum_history": { ... }, ..., "all_met": true },
  "...": "..."
}
```

### 3.3 TypeScript 타입 정의 (프론트엔드 참고)

```typescript
interface CriterionResult {
  met: boolean;
  reason?: string | null;
  is_52w_high?: boolean;       // 전고점 돌파 전용
  had_limit_up?: boolean;      // 끼 보유 전용
  had_15pct_rise?: boolean;    // 끼 보유 전용
  ma_values?: Record<string, number>;  // 정배열 전용
}

interface StockCriteria {
  high_breakout: CriterionResult;
  momentum_history: CriterionResult;
  resistance_breakout: CriterionResult;
  ma_alignment: CriterionResult;
  supply_demand: CriterionResult;
  program_trading: CriterionResult;
  top30_trading_value: CriterionResult;
  all_met: boolean;  // 7개 기준 모두 met === true
}
```

### 3.4 기준 키(key) 매핑 테이블

| 순번 | 기준명 | 키 (key) | 색상 |
|------|--------|----------|------|
| 1 | 전고점 돌파 | `high_breakout` | 빨간색 |
| 2 | 끼 보유 | `momentum_history` | 주황색 |
| 3 | 심리적 저항선 돌파 | `resistance_breakout` | 노랑색 |
| 4 | 이동평균선 정배열 | `ma_alignment` | 청록색 |
| 5 | 외국인/기관 수급 | `supply_demand` | 파란색 |
| 6 | 프로그램 매매 | `program_trading` | 보라색 |
| 7 | 거래대금 TOP30 | `top30_trading_value` | 자홍색 |

---

## 4. 프론트엔드 시각화 명세

### 4.1 인디케이터 표시 규칙

| 규칙 | 설명 |
|------|------|
| 표시 대상 | **Admin 사용자**에게만 표시 |
| 표시 위치 | 종목명 하단, 종목 코드 아래 |
| 표시 내용 | 충족된(`met === true`) 기준만 표시 |
| 정렬 순서 | 기준 1~7 순서 고정 (빨-주-노-청록-파-보라-자홍) |
| 비충족 기준 | 표시하지 않음 (공간 미확보) |

**표시 조건 판정**:

```
showCriteria = isAdmin === true AND criteria !== null AND criteria !== undefined
```

---

### 4.2 반응형 디자인

#### 모바일 (화면 너비 < 640px): 색상 도트

- **형태**: 원형 도트
- **크기**: 2.5 x 2.5 단위 (약 10px x 10px)
- **배치**: 가로 나열, 간격 4px, 줄 바꿈 허용
- **인터랙션**: 도트 클릭 시 판정 근거 팝업 표시
- **특수 규칙**: `is_52w_high === true`일 때 빨간 도트 **2개** 표시
- **효과**: hover 시 1.25배 확대, 그림자 효과

#### PC/태블릿 (화면 너비 >= 640px): 뱃지

- **형태**: 색상 배경 + 짧은 텍스트 라벨이 포함된 뱃지
- **크기**: 내부 padding `1.5단위 x 0.5단위`, 폰트 사이즈 9px
- **모양**: 완전 둥근 형태 (border-radius: full)
- **구성**: 좌측에 1.5 x 1.5 크기의 색상 도트 + 우측에 텍스트 라벨
- **인터랙션**: 뱃지 클릭 시 판정 근거 팝업 표시
- **특수 규칙**: `is_52w_high === true`일 때 뱃지 텍스트가 `"52주 신고가"`로 변경

---

### 4.3 색상 매핑 테이블

| 기준 | 도트 색상 | 뱃지 배경색 | 뱃지 텍스트색 | 짧은 라벨 | 52주 신고가 라벨 |
|------|----------|-----------|-------------|----------|---------------|
| 전고점 돌파 | `red-500` | `red-100` | `red-700` | 전고점 | 52주 신고가 |
| 끼 보유 | `orange-500` | `orange-100` | `orange-700` | 끼 | - |
| 저항선 돌파 | `yellow-400` | `yellow-100` | `yellow-700` | 저항선 | - |
| 정배열 | `teal-500` | `teal-100` | `teal-700` | 정배열 | - |
| 외국인/기관 | `blue-500` | `blue-100` | `blue-700` | 수급 | - |
| 프로그램 매매 | `violet-500` | `violet-100` | `violet-700` | 프로그램 | - |
| 거래대금 TOP30 | `fuchsia-500` | `fuchsia-100` | `fuchsia-700` | TOP30 | - |

> 색상 값은 Tailwind CSS의 기본 팔레트 기준이다. 다른 CSS 프레임워크 사용 시 해당 색상의 HEX/RGB 값으로 변환하여 적용한다.

**참고 색상 HEX 값** (Tailwind CSS 기본):

| 색상 토큰 | HEX 값 |
|-----------|--------|
| red-500 | `#ef4444` |
| red-100 | `#fee2e2` |
| red-700 | `#b91c1c` |
| orange-500 | `#f97316` |
| orange-100 | `#ffedd5` |
| orange-700 | `#c2410c` |
| yellow-400 | `#facc15` |
| yellow-100 | `#fef9c3` |
| yellow-700 | `#a16207` |
| teal-500 | `#14b8a6` |
| teal-100 | `#ccfbf1` |
| teal-700 | `#0f766e` |
| blue-500 | `#3b82f6` |
| blue-100 | `#dbeafe` |
| blue-700 | `#1d4ed8` |
| violet-500 | `#8b5cf6` |
| violet-100 | `#ede9fe` |
| violet-700 | `#6d28d9` |
| fuchsia-500 | `#d946ef` |
| fuchsia-100 | `#fae8ff` |
| fuchsia-700 | `#a21caf` |

---

### 4.4 전체 기준 충족 효과 (all_met)

7개 기준이 **모두** `met === true`일 때 (`all_met === true`) 특별한 시각적 효과를 적용한다.

#### 카드 모드 (상세 보기)

| 속성 | 값 | 설명 |
|------|-----|------|
| 테두리 | `ring-2 ring-yellow-400` (투명도 70%) | 금색 링 테두리 |
| 그림자 | `box-shadow: 0 0 12px rgba(234,179,8,0.3)` | 금색 그림자 |
| 애니메이션 | `shimmer` (3초 주기) | 금색 빛 펄스 효과 |

#### 컴팩트 모드 (목록형)

| 속성 | 값 | 설명 |
|------|-----|------|
| 좌측 보더 | 3px 두께, `yellow-400` 색상 | 금색 좌측 강조선 |
| 배경색 | `yellow-50` (투명도 40%) | 연한 노란 배경 하이라이트 |

---

### 4.5 클릭 팝업 (카드 모드 전용)

인디케이터(도트 또는 뱃지)를 클릭하면 해당 기준의 판정 근거를 보여주는 팝업이 표시된다.

#### 팝업 구성

```
+--------------------------------------+
| [색상 도트] 기준명              [X]  |
|--------------------------------------|
| 판정 근거 (reason) 텍스트             |
+--------------------------------------+
```

#### 팝업 스타일

| 속성 | 값 |
|------|-----|
| 위치 | 인디케이터 바로 아래 (absolute, top: 100%) |
| 너비 | 모바일: 256px, PC: 288px |
| 배경 | 시스템 팝오버 배경색 |
| 테두리 | 1px, 시스템 보더 색상 |
| 모서리 | border-radius: 8px |
| 그림자 | large shadow |
| z-index | 50 |

#### 팝업 동작

- 같은 인디케이터 재클릭 시 팝업 닫기 (토글)
- 다른 인디케이터 클릭 시 해당 기준의 팝업으로 전환
- X 버튼 클릭 시 팝업 닫기
- 이벤트 버블링 차단 (`preventDefault`, `stopPropagation`)

---

### 4.6 범례 (Legend)

모든 기준 색상과 라벨을 한눈에 볼 수 있는 범례 컴포넌트를 제공한다.

#### 표시 조건

```
showLegend = isAdmin === true AND criteria_data !== null AND criteria_data !== undefined
```

#### 범례 구성

```
선정 기준: [빨강●] 전고점 돌파  [주황●] 끼 보유  [노랑●] 저항선 돌파  [청록●] 정배열
          [파랑●] 외국인/기관 수급  [보라●] 프로그램 매매  [자홍●] 거래대금 TOP30
          [금색○] 전체 충족
```

#### 범례 스타일

| 속성 | 값 |
|------|-----|
| 배경 | muted 색상 (투명도 40%) |
| 모서리 | border-radius: 8px |
| 배치 | flex, wrap 허용, 항목 간 수평 간격 12px, 수직 간격 4px |
| 도트 크기 | 모바일: 8px, PC: 10px |
| 폰트 크기 | 모바일: 10px, PC: 12px |
| "전체 충족" 도트 | 금색 배경(투명도 30%) + 금색 ring 1px |

---

### 4.7 컴팩트 모드 (목록형)

종목을 표 형태의 컴팩트한 행으로 표시할 때의 인디케이터 명세이다.

#### 도트 표시

| 속성 | 값 |
|------|-----|
| 크기 | 1.5 x 1.5 단위 (약 6px x 6px) |
| 배치 | 종목명 아래, 가로 나열 |
| 간격 | 1px (매우 좁은 간격) |
| 인터랙션 | **없음** (행 전체가 외부 링크이므로 클릭 팝업 미제공) |

#### all_met 효과 (컴팩트 모드)

| 속성 | 값 |
|------|-----|
| 좌측 보더 | 3px 두께, `yellow-400` 색상 |
| 배경색 | `yellow-50` (투명도 40%), sticky 영역에만 적용 |
| 일반 배경 | 기본 카드 배경색 유지 |

---

## 5. CSS 애니메이션 명세

### 5.1 Shimmer 애니메이션 (전체 충족 효과)

전체 기준 충족 종목 카드에 적용하는 금색 빛 펄스 애니메이션이다.

```css
@keyframes shimmer {
  0%, 100% {
    box-shadow: 0 0 6px 1px rgba(234, 179, 8, 0.25);
  }
  50% {
    box-shadow: 0 0 20px 4px rgba(234, 179, 8, 0.5);
  }
}
```

| 속성 | 값 |
|------|-----|
| 키프레임 | `shimmer` |
| 주기 | 3초 (`3s`) |
| 타이밍 함수 | `ease-in-out` |
| 반복 | `infinite` (무한 반복) |
| 색상 | `rgba(234, 179, 8, ...)` (Tailwind `yellow-500` 계열) |
| 최소 그림자 | `0 0 6px 1px` (투명도 0.25) |
| 최대 그림자 | `0 0 20px 4px` (투명도 0.5) |

#### 적용 방법

```css
.all-criteria-met-card {
  animation: shimmer 3s ease-in-out infinite;
}
```

### 5.2 도트 Hover 효과

```css
.criteria-dot {
  transition: transform 0.15s ease;
}

.criteria-dot:hover {
  transform: scale(1.25);
}
```

### 5.3 뱃지 Hover 효과

```css
.criteria-badge {
  transition: opacity 0.15s ease;
}

.criteria-badge:hover {
  opacity: 0.8;
}
```

---

## 6. 백엔드-프론트엔드 데이터 흐름

### 6.1 전체 흐름도

```
[데이터 소스]          [백엔드 처리]              [전송]        [프론트엔드]
     |                     |                      |               |
     |  일봉 데이터 수집    |                      |               |
     |-------------------->|                      |               |
     |  펀더멘탈 데이터 수집 |                      |               |
     |-------------------->|                      |               |
     |  수급 데이터 수집     |                      |               |
     |-------------------->|                      |               |
     |  거래대금 순위 수집   |                      |               |
     |-------------------->|                      |               |
     |                     |                      |               |
     |                     | 종목별 7개 기준 평가   |               |
     |                     |---+                  |               |
     |                     |   | criteria_data    |               |
     |                     |<--+ 생성             |               |
     |                     |                      |               |
     |                     | JSON 파일 export      |               |
     |                     |--------------------->|               |
     |                     |  (criteria_data 포함) |               |
     |                     |                      |               |
     |                     |                      | JSON fetch    |
     |                     |                      |<--------------|
     |                     |                      |               |
     |                     |                      | criteria_data |
     |                     |                      |-------------->|
     |                     |                      |               |
     |                     |                      |  Admin 확인   |
     |                     |                      |  인디케이터    |
     |                     |                      |  렌더링       |
```

### 6.2 단계별 상세

#### Step 1: 데이터 수집 (백엔드)

백엔드는 주식 시장 API(증권사 API, 거래소 API 등)로부터 다음 데이터를 수집한다.

| 데이터 | 용도 | 비고 |
|--------|------|------|
| 일봉 OHLCV (최소 120일) | 기준 1, 2, 4 | 고가, 종가, 기준가, 등락률 |
| 52주 최고가 | 기준 1 | 펀더멘탈 데이터에서 추출 |
| 프로그램 순매수 수량 | 기준 6 | 펀더멘탈 데이터에서 추출 |
| 외국인/기관 순매수 | 기준 5 | 투자자별 수급 데이터 |
| 거래대금 상위 종목 | 기준 7 | 시장별 TOP30 |
| 현재가, 전일종가 | 기준 1, 3 | 실시간 시세 |

#### Step 2: 기준 평가 (백엔드)

수집된 데이터를 기반으로 각 종목에 대해 7개 기준을 개별 평가한다.

```
for each stock in all_stocks:
    criteria = {
        "high_breakout":      check_high_breakout(stock, daily_prices, w52_high),
        "momentum_history":   check_momentum_history(daily_prices),
        "resistance_breakout": check_resistance_breakout(current_price, prev_close),
        "ma_alignment":       check_ma_alignment(current_price, daily_prices),
        "supply_demand":      check_supply_demand(foreign_net, institution_net),
        "program_trading":    check_program_trading(program_net_buy_qty),
        "top30_trading_value": check_top30_trading_value(stock_code, top30_codes),
    }
    criteria["all_met"] = all(c["met"] for c in criteria.values())
    result[stock.code] = criteria
```

#### Step 3: JSON Export (백엔드 -> 프론트엔드)

평가 결과를 `criteria_data` 필드로 포함하여 JSON 파일로 내보낸다.

```json
{
  "timestamp": "2026-02-18T15:30:00+09:00",
  "rising": { "kospi": [...], "kosdaq": [...] },
  "falling": { "kospi": [...], "kosdaq": [...] },
  "criteria_data": {
    "005930": {
      "high_breakout": { "met": true, "is_52w_high": false, "reason": "..." },
      "momentum_history": { "met": false, "had_limit_up": false, "had_15pct_rise": false, "reason": null },
      "resistance_breakout": { "met": false, "reason": null },
      "ma_alignment": { "met": true, "ma_values": { ... }, "reason": "..." },
      "supply_demand": { "met": true, "reason": "..." },
      "program_trading": { "met": false, "reason": "..." },
      "top30_trading_value": { "met": true, "reason": "..." },
      "all_met": false
    },
    "000660": { ... },
    "...": "..."
  }
}
```

#### Step 4: 프론트엔드 데이터 수신

프론트엔드는 JSON 파일을 fetch하여 `criteria_data`를 추출하고, 각 종목 카드/행 컴포넌트에 해당 종목의 criteria 결과를 전달한다.

```
fetch JSON -> extract criteria_data
for each stock_card:
    criteria = criteria_data[stock.code]
    render(stock_card, criteria)
```

> **캐시 주의**: criteria_data는 장중 실시간으로 변경되므로, fetch 시 캐시를 비활성화(`cache: "no-store"` 또는 동등한 설정)하여 최신 데이터를 보장해야 한다.

#### Step 5: Admin 확인 후 렌더링

```
if isAdmin AND criteria exists:
    render criteria indicators
    if criteria.all_met:
        apply gold highlight effect
else:
    do not render any criteria indicators
```

### 6.3 에러 처리

| 상황 | 대응 |
|------|------|
| criteria_data가 null/undefined | 인디케이터 비표시 (정상 동작, Admin 아닌 경우와 동일) |
| 특정 종목의 criteria 없음 | 해당 종목 인디케이터 비표시 |
| reason이 null | 팝업에 "근거 없음" 표시 |
| 일봉 데이터 부족 (< 120일) | MA 계산 불가 시 해당 기준 `met = false` + 사유 기재 |
| 수급/펀더멘탈 데이터 미수집 | 해당 기준 `met = false` (데이터 없음 = 미충족) |

---

## 부록

### A. 통합 평가 함수 의사코드

```
function evaluate_stock_criteria(stock, daily_prices, fundamental, investor_info, top30_codes):
    current_price = stock.current_price
    prev_close = current_price - stock.change_price

    w52_high = fundamental.w52_high (if exists)
    program_qty = fundamental.program_net_buy_qty (if exists)

    criteria = {
        "high_breakout":       check_high_breakout(current_price, daily_prices, w52_high),
        "momentum_history":    check_momentum_history(daily_prices),
        "resistance_breakout": check_resistance_breakout(current_price, prev_close),
        "ma_alignment":        check_ma_alignment(current_price, daily_prices),
        "supply_demand":       check_supply_demand(investor_info.foreign_net, investor_info.institution_net),
        "program_trading":     check_program_trading(program_qty),
        "top30_trading_value": check_top30_trading_value(stock.code, top30_codes),
    }

    criteria["all_met"] = all criteria[key].met == true for all 7 keys

    return criteria


function evaluate_all_stocks(stocks, daily_data, fundamental_data, investor_data, top30_data):
    top30_codes = extract_top30_code_set(top30_data)  # 시장별 TOP30 합산

    result = {}
    for each stock in stocks:
        daily_prices = daily_data[stock.code]
        fundamental = fundamental_data[stock.code]
        investor_info = investor_data[stock.code]

        result[stock.code] = evaluate_stock_criteria(
            stock, daily_prices, fundamental, investor_info, top30_codes
        )

    return result
```

### B. 프론트엔드 인디케이터 렌더링 의사코드

```
CRITERIA_CONFIG = [
    { key: "high_breakout",       dot_color: "red-500",    badge_bg: "red-100",    badge_text: "red-700",    label: "전고점 돌파",       short: "전고점" },
    { key: "momentum_history",    dot_color: "orange-500", badge_bg: "orange-100", badge_text: "orange-700", label: "끼 보유",          short: "끼" },
    { key: "resistance_breakout", dot_color: "yellow-400", badge_bg: "yellow-100", badge_text: "yellow-700", label: "저항선 돌파",       short: "저항선" },
    { key: "ma_alignment",        dot_color: "teal-500",    badge_bg: "teal-100",    badge_text: "teal-700",    label: "정배열",           short: "정배열" },
    { key: "supply_demand",       dot_color: "blue-500",    badge_bg: "blue-100",    badge_text: "blue-700",    label: "외국인/기관 수급",  short: "수급" },
    { key: "program_trading",     dot_color: "violet-500",  badge_bg: "violet-100",  badge_text: "violet-700",  label: "프로그램 매매",     short: "프로그램" },
    { key: "top30_trading_value", dot_color: "fuchsia-500", badge_bg: "fuchsia-100", badge_text: "fuchsia-700", label: "거래대금 TOP30",   short: "TOP30" },
]

function render_criteria_indicators(criteria, isAdmin):
    if NOT isAdmin OR criteria is null:
        return nothing

    for each config in CRITERIA_CONFIG:
        criterion = criteria[config.key]
        if criterion.met is false:
            continue

        is_52w = (config.key == "high_breakout" AND criterion.is_52w_high == true)

        # 모바일 (< 640px)
        render dot(config.dot_color, size=2.5)
        if is_52w:
            render dot(config.dot_color, size=2.5)  # 두 번째 도트

        # PC/태블릿 (>= 640px)
        label = "52주 신고가" if is_52w else config.short
        render badge(config.badge_bg, config.badge_text, config.dot_color, label)
```

### C. 한국 주식 시장 호가 단위표 (참고)

| 가격 범위 | 호가 단위 |
|-----------|----------|
| 2,000원 미만 | 1원 |
| 2,000원 이상 ~ 5,000원 미만 | 5원 |
| 5,000원 이상 ~ 20,000원 미만 | 10원 |
| 20,000원 이상 ~ 50,000원 미만 | 50원 |
| 50,000원 이상 ~ 200,000원 미만 | 100원 |
| 200,000원 이상 ~ 500,000원 미만 | 500원 |
| 500,000원 이상 | 1,000원 |

> 이 표는 2024년 기준 한국거래소 호가 단위이다. 거래소 규정 변경 시 TICK_BOUNDARIES 값을 함께 업데이트해야 한다.
