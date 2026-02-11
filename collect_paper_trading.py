"""
모의투자 데이터 수집 스크립트

Gemini AI가 오전에 선정한 대장주를 1주씩 매수했다고 가정하고,
장 마감 종가에 매도 시 수익률을 계산합니다.

사용법:
  python collect_paper_trading.py          # 일반 실행 (JSON 파일 저장)
  python collect_paper_trading.py --test   # 테스트 (콘솔 출력만)
  python collect_paper_trading.py --stocks 005930,000660  # 수동 종목 지정
"""
from __future__ import annotations

import json
import argparse
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from modules.kis_client import KISClient

# 프로젝트 경로
ROOT_DIR = Path(__file__).parent
DATA_DIR = ROOT_DIR / "frontend" / "public" / "data"
PAPER_TRADING_DIR = DATA_DIR / "paper-trading"
INDEX_PATH = DATA_DIR / "paper-trading-index.json"
LATEST_PATH = DATA_DIR / "latest.json"

# 보관 기간 (일)
RETENTION_DAYS = 30


def load_latest_json() -> dict:
    """latest.json 로드"""
    if not LATEST_PATH.exists():
        raise FileNotFoundError(f"latest.json이 없습니다: {LATEST_PATH}")

    with open(LATEST_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def get_all_latest_snapshots(today_str: str) -> list[dict]:
    """git 히스토리에서 오늘 모든 latest.json 버전 추출 (시간순 정렬)"""
    relative_path = "frontend/public/data/latest.json"

    try:
        # 오늘 커밋 해시 조회
        result = subprocess.run(
            [
                "git", "log", "--format=%H",
                f"--since={today_str} 00:00:00 +0900",
                "--", relative_path,
            ],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0 or not result.stdout.strip():
            print("[스냅샷] git 히스토리 없음 (fallback: 현재 파일)")
            return []

        hashes = result.stdout.strip().split("\n")
        print(f"[스냅샷] 오늘 latest.json 커밋 {len(hashes)}개 발견")

        snapshots = []
        for commit_hash in hashes:
            try:
                show_result = subprocess.run(
                    ["git", "show", f"{commit_hash}:{relative_path}"],
                    capture_output=True, text=True, timeout=30,
                )
                if show_result.returncode != 0:
                    continue
                data = json.loads(show_result.stdout)
                timestamp = data.get("timestamp", "")
                if timestamp:
                    snapshots.append({
                        "timestamp": timestamp,
                        "data": data,
                    })
            except (json.JSONDecodeError, subprocess.TimeoutExpired):
                continue

        # 시간순 정렬 (oldest first)
        snapshots.sort(key=lambda s: s["timestamp"])

        # 중복 timestamp 제거
        seen = set()
        unique = []
        for s in snapshots:
            if s["timestamp"] not in seen:
                seen.add(s["timestamp"])
                unique.append(s)

        print(f"[스냅샷] 유효 스냅샷 {len(unique)}개 (시간순)")
        for s in unique:
            print(f"  - {s['timestamp']}")

        return unique

    except (subprocess.TimeoutExpired, FileNotFoundError):
        print("[스냅샷] git 명령 실행 실패 (fallback: 현재 파일)")
        return []


def extract_leader_stocks(data: dict) -> list[dict]:
    """theme_analysis에서 대장주 추출"""
    theme_analysis = data.get("theme_analysis")
    if not theme_analysis:
        print("[경고] theme_analysis가 없습니다.")
        return []

    stocks = []
    seen_codes = set()

    for theme in theme_analysis.get("themes", []):
        theme_name = theme.get("theme_name", "")
        for stock in theme.get("leader_stocks", []):
            code = stock.get("code", "")
            name = stock.get("name", "")
            if code and code not in seen_codes:
                seen_codes.add(code)
                stocks.append({
                    "code": code,
                    "name": name,
                    "theme": theme_name,
                })

    return stocks


def find_morning_price(data: dict, code: str) -> Optional[int]:
    """latest.json의 모든 섹션에서 종목의 오전 current_price 찾기"""
    sections = ["rising", "falling", "volume", "trading_value"]
    for section in sections:
        section_data = data.get(section, {})
        for market in ["kospi", "kosdaq"]:
            for stock in section_data.get(market, []):
                if stock.get("code") == code:
                    return stock.get("current_price")

    # fluctuation 섹션도 검색
    for section in ["fluctuation", "fluctuation_direct"]:
        section_data = data.get(section, {})
        for key in ["kospi_up", "kospi_down", "kosdaq_up", "kosdaq_down"]:
            for stock in section_data.get(key, []):
                if stock.get("code") == code:
                    return stock.get("current_price")

    return None


def get_stock_prices(client: KISClient, code: str) -> Optional[dict]:
    """KIS API로 종가 + 최고가 조회"""
    try:
        result = client.get_stock_price(code)
        if result.get("rt_cd") == "0":
            output = result.get("output", {})
            close_str = output.get("stck_prpr", "0")
            high_str = output.get("stck_hgpr", "0")
            close_price = int(close_str) if close_str else None
            high_price = int(high_str) if high_str else None
            if close_price is None:
                return None
            return {
                "close_price": close_price,
                "high_price": high_price if high_price else close_price,
            }
        else:
            print(f"  [오류] {code} API 응답: {result.get('msg1', 'Unknown')}")
            return None
    except Exception as e:
        print(f"  [오류] {code} 가격 조회 실패: {e}")
        return None


def find_high_price_time(client: KISClient, code: str, high_price: int) -> Optional[str]:
    """분봉 데이터에서 최고가 달성 시간 찾기"""
    path = "/uapi/domestic-stock/v1/quotations/inquire-time-itemchartprice"
    tr_id = "FHKST03010200"
    cursor = "153000"

    for _ in range(15):
        params = {
            "FID_ETC_CLS_CODE": "",
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_INPUT_ISCD": code,
            "FID_INPUT_HOUR_1": cursor,
            "FID_PW_DATA_INCU_YN": "N",
        }
        try:
            result = client.request("GET", path, tr_id, params=params)
            items = result.get("output2", [])
            if not items:
                break
            for item in items:
                candle_high = int(item.get("stck_hgpr", "0"))
                if candle_high >= high_price:
                    t = item.get("stck_cntg_hour", "")
                    if t:
                        return f"{t[:2]}:{t[2:4]}"
            cursor = items[-1].get("stck_cntg_hour", "")
            if not cursor or cursor <= "090000":
                break
            time.sleep(0.1)
        except Exception:
            break

    return None


def collect_paper_trading_data(
    stocks_override: Optional[list[str]] = None,
    test_mode: bool = False,
) -> Optional[dict]:
    """모의투자 데이터 수집"""
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")

    # git 히스토리에서 오늘 모든 스냅샷 수집
    snapshots = get_all_latest_snapshots(today_str)

    if snapshots:
        # 첫 번째(가장 이른) 스냅샷을 기본 매수가로 사용
        data = snapshots[0]["data"]
        morning_timestamp = snapshots[0]["timestamp"]
    else:
        # fallback: 현재 latest.json
        data = load_latest_json()
        morning_timestamp = data.get("timestamp", "")

    # 대장주 추출
    if stocks_override:
        # 수동 지정 종목
        leader_stocks = [
            {"code": code.strip(), "name": code.strip(), "theme": "수동 지정"}
            for code in stocks_override
        ]
    else:
        leader_stocks = extract_leader_stocks(data)

    if not leader_stocks:
        print("[결과] 대장주가 없습니다.")
        return None

    print(f"\n[모의투자] 대장주 {len(leader_stocks)}종목 수집 시작")
    print(f"  오전 데이터: {morning_timestamp}")

    # price_snapshots 구성: 각 스냅샷에서 대장주 가격 추출
    leader_codes = [s["code"] for s in leader_stocks]
    price_snapshots = []
    for snap in snapshots:
        snap_prices = {}
        for code in leader_codes:
            price = find_morning_price(snap["data"], code)
            if price is not None:
                snap_prices[code] = price
        if snap_prices:
            price_snapshots.append({
                "timestamp": snap["timestamp"],
                "prices": snap_prices,
            })

    if price_snapshots:
        print(f"\n[스냅샷] 대장주 가격 스냅샷 {len(price_snapshots)}개 생성")

    # KIS 클라이언트 초기화
    client = KISClient()

    results = []
    for i, stock in enumerate(leader_stocks):
        code = stock["code"]
        name = stock["name"]
        theme = stock["theme"]

        # 오전 매수가 (첫 번째 스냅샷 기준)
        buy_price = find_morning_price(data, code)
        if buy_price is None:
            print(f"  [{i+1}/{len(leader_stocks)}] {name}({code}) - 오전 가격 없음, 건너뜀")
            continue

        # 종가 조회 (API 호출 간격)
        if i > 0:
            time.sleep(0.3)

        prices = get_stock_prices(client, code)
        if prices is None:
            print(f"  [{i+1}/{len(leader_stocks)}] {name}({code}) - 가격 조회 실패, 건너뜀")
            continue

        close_price = prices["close_price"]
        high_price = prices["high_price"]

        # 최고가 달성 시간 조회
        high_time = find_high_price_time(client, code, high_price)

        # 종가 기준 수익률
        profit_amount = close_price - buy_price
        profit_rate = round((profit_amount / buy_price) * 100, 2) if buy_price > 0 else 0

        # 최고가 기준 수익률
        high_profit_amount = high_price - buy_price
        high_profit_rate = round((high_profit_amount / buy_price) * 100, 2) if buy_price > 0 else 0

        results.append({
            "code": code,
            "name": name,
            "theme": theme,
            "buy_price": buy_price,
            "close_price": close_price,
            "profit_rate": profit_rate,
            "profit_amount": profit_amount,
            "high_price": high_price,
            "high_time": high_time,
            "high_profit_rate": high_profit_rate,
            "high_profit_amount": high_profit_amount,
        })

        sign = "+" if profit_rate >= 0 else ""
        print(f"  [{i+1}/{len(leader_stocks)}] {name}({code}): {buy_price:,} -> {close_price:,} ({sign}{profit_rate}%) [최고 {high_price:,}]")

    if not results:
        print("[결과] 수집된 종목이 없습니다.")
        return None

    # 종가 기준 요약 계산
    profit_stocks = sum(1 for r in results if r["profit_rate"] > 0)
    loss_stocks = sum(1 for r in results if r["profit_rate"] < 0)
    total_invested = sum(r["buy_price"] for r in results)
    total_value = sum(r["close_price"] for r in results)
    total_profit = total_value - total_invested
    total_profit_rate = round((total_profit / total_invested) * 100, 2) if total_invested > 0 else 0

    # 최고가 기준 요약 계산
    high_profit_stocks = sum(1 for r in results if r["high_profit_rate"] > 0)
    high_loss_stocks = sum(1 for r in results if r["high_profit_rate"] < 0)
    high_total_value = sum(r["high_price"] for r in results)
    high_total_profit = high_total_value - total_invested
    high_total_profit_rate = round((high_total_profit / total_invested) * 100, 2) if total_invested > 0 else 0

    trade_date = now.strftime("%Y-%m-%d")
    collected_at = now.strftime("%Y-%m-%d %H:%M:%S")

    result_data = {
        "trade_date": trade_date,
        "morning_timestamp": morning_timestamp,
        "collected_at": collected_at,
        **({"price_snapshots": price_snapshots} if price_snapshots else {}),
        "stocks": results,
        "summary": {
            "total_stocks": len(results),
            "profit_stocks": profit_stocks,
            "loss_stocks": loss_stocks,
            "total_invested": total_invested,
            "total_value": total_value,
            "total_profit": total_profit,
            "total_profit_rate": total_profit_rate,
            "high_total_value": high_total_value,
            "high_total_profit": high_total_profit,
            "high_total_profit_rate": high_total_profit_rate,
            "high_profit_stocks": high_profit_stocks,
            "high_loss_stocks": high_loss_stocks,
        },
    }

    # 결과 요약 출력
    print(f"\n[모의투자 결과]")
    print(f"  날짜: {trade_date}")
    print(f"  종목수: {len(results)} (수익 {profit_stocks} / 손실 {loss_stocks})")
    print(f"  투자금: {total_invested:,}원")
    print(f"  평가금: {total_value:,}원")
    sign = "+" if total_profit >= 0 else ""
    print(f"  수익금: {sign}{total_profit:,}원 ({sign}{total_profit_rate}%)")

    return result_data


def save_paper_trading_data(result_data: dict):
    """JSON 파일 저장 + 인덱스 갱신"""
    trade_date = result_data["trade_date"]

    # 디렉토리 생성
    PAPER_TRADING_DIR.mkdir(parents=True, exist_ok=True)

    # 일별 파일 저장
    file_path = PAPER_TRADING_DIR / f"{trade_date}.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(result_data, f, ensure_ascii=False, indent=2)
    print(f"\n[저장] {file_path}")

    # 인덱스 갱신
    update_index(result_data)

    # 30일 이전 파일 정리
    cleanup_old_files()


def update_index(result_data: dict):
    """인덱스 파일 갱신"""
    # 기존 인덱스 로드
    if INDEX_PATH.exists():
        with open(INDEX_PATH, "r", encoding="utf-8") as f:
            index = json.load(f)
    else:
        index = {"updated_at": "", "entries": []}

    trade_date = result_data["trade_date"]
    summary = result_data["summary"]

    new_entry = {
        "date": trade_date,
        "filename": f"{trade_date}.json",
        "total_profit_rate": summary["total_profit_rate"],
        "stock_count": summary["total_stocks"],
    }

    # 같은 날짜 항목 업데이트 또는 추가
    entries = index.get("entries", [])
    found = False
    for i, entry in enumerate(entries):
        if entry["date"] == trade_date:
            entries[i] = new_entry
            found = True
            break
    if not found:
        entries.append(new_entry)

    # 날짜 내림차순 정렬
    entries.sort(key=lambda e: e["date"], reverse=True)

    index["updated_at"] = result_data["collected_at"]
    index["entries"] = entries

    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
    print(f"[저장] {INDEX_PATH}")


def cleanup_old_files():
    """30일 이전 파일 정리"""
    cutoff = datetime.now() - timedelta(days=RETENTION_DAYS)
    cutoff_str = cutoff.strftime("%Y-%m-%d")

    removed = 0
    for file in PAPER_TRADING_DIR.glob("*.json"):
        if file.stem < cutoff_str:
            file.unlink()
            removed += 1

    if removed:
        print(f"[정리] {removed}개 오래된 파일 삭제")

    # 인덱스에서도 제거
    if INDEX_PATH.exists():
        with open(INDEX_PATH, "r", encoding="utf-8") as f:
            index = json.load(f)

        entries = index.get("entries", [])
        original_count = len(entries)
        entries = [e for e in entries if e["date"] >= cutoff_str]

        if len(entries) < original_count:
            index["entries"] = entries
            with open(INDEX_PATH, "w", encoding="utf-8") as f:
                json.dump(index, f, ensure_ascii=False, indent=2)


def main():
    parser = argparse.ArgumentParser(description="모의투자 데이터 수집")
    parser.add_argument("--test", action="store_true", help="테스트 모드 (저장 없이 콘솔 출력만)")
    parser.add_argument("--stocks", type=str, help="수동 종목 지정 (쉼표 구분, 예: 005930,000660)")
    args = parser.parse_args()

    stocks_override = args.stocks.split(",") if args.stocks else None

    result_data = collect_paper_trading_data(
        stocks_override=stocks_override,
        test_mode=args.test,
    )

    if result_data and not args.test:
        save_paper_trading_data(result_data)
    elif args.test:
        print("\n[테스트 모드] 파일 저장을 건너뜁니다.")


if __name__ == "__main__":
    main()
