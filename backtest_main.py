"""
예측 백테스팅 — 메인 실행 스크립트

Supabase의 active 예측을 조회하고, 실제 주가와 비교하여 적중 여부를 판정합니다.

Usage:
    python backtest_main.py          # 전체 실행
    python backtest_main.py --test   # 테스트 (Supabase 업데이트 건너뜀)
"""
import json
import sys
from datetime import datetime, timedelta

from config.settings import *  # noqa: F401,F403 — 환경변수 로드
from modules.backtest import (
    get_active_predictions,
    fetch_stock_returns,
    fetch_index_return,
    evaluate_prediction,
    update_prediction_status,
    calculate_accuracy_report,
)
from modules.utils import KST


def main():
    test_mode = "--test" in sys.argv

    if test_mode:
        print("🧪 테스트 모드 (Supabase 업데이트 건너뜀)")

    print("=" * 50)
    print("📊 예측 백테스팅 시작")
    print("=" * 50)

    # Supabase 연결
    try:
        from modules.supabase_client import get_supabase_manager
        manager = get_supabase_manager()
        client = manager._get_client()
        if not client:
            print("  ✗ Supabase 연결 불가")
            sys.exit(1)
    except Exception as e:
        print(f"  ✗ Supabase 초기화 실패: {e}")
        sys.exit(1)

    # Step 1: Active 예측 조회
    print("\n[1/4] Active 예측 조회...")
    predictions = get_active_predictions(client)
    print(f"  ✓ {len(predictions)}건의 active 예측 조회")

    if not predictions:
        print("  평가할 예측이 없습니다")
        print("\n✅ 백테스팅 완료")
        return

    # Step 2: 대장주 종목코드 수집 + 카테고리별 수익률 조회
    print("\n[2/4] 주식 수익률 조회...")
    all_codes = set()
    for pred in predictions:
        leader_stocks = pred.get("leader_stocks", "[]")
        if isinstance(leader_stocks, str):
            try:
                leader_stocks = json.loads(leader_stocks)
            except json.JSONDecodeError:
                leader_stocks = []
        for s in leader_stocks:
            code = s.get("code", "")
            if code:
                all_codes.add(code)

    # 카테고리별 평가 기간 (영업일 기준이지만 yfinance는 달력일로 조회)
    end_date = datetime.now(KST).strftime("%Y-%m-%d")
    category_periods = {
        "today": 3,       # 1 영업일 ≈ 3 달력일 (주말 포함 여유)
        "short_term": 12,  # 7 영업일 ≈ 12 달력일
        "long_term": 45,   # 30 영업일 ≈ 45 달력일
    }

    # 카테고리별 수익률 + 지수 수익률 캐시
    returns_by_category = {}
    index_by_category = {}
    for cat, cal_days in category_periods.items():
        start = (datetime.now(KST) - timedelta(days=cal_days)).strftime("%Y-%m-%d")
        if all_codes:
            returns_by_category[cat] = fetch_stock_returns(list(all_codes), start, end_date)
        else:
            returns_by_category[cat] = {}
        index_by_category[cat] = fetch_index_return(start, end_date)

    total_codes = sum(len(r) for r in returns_by_category.values())
    print(f"  ✓ 카테고리별 수익률 조회 완료 (종목 {len(all_codes)}개)")
    for cat in category_periods:
        print(f"    - {cat}: KOSPI {index_by_category[cat]:+.2f}%, 종목 {len(returns_by_category[cat])}개")

    # Step 3: 예측 평가
    print("\n[3/4] 예측 평가...")
    results = {"hit": 0, "missed": 0, "expired": 0, "active": 0}

    for pred in predictions:
        category = pred.get("category", "today")
        returns = returns_by_category.get(category, {})
        index_return = index_by_category.get(category, 0.0)

        status = evaluate_prediction(pred, returns, index_return)
        results[status] += 1

        theme_name = pred.get("theme_name", "N/A")

        if status in ("hit", "missed", "expired"):
            print(f"  [{status.upper()}] {theme_name} ({category})")

            if not test_mode:
                # 수익률 정보 수집
                leader_stocks = pred.get("leader_stocks", "[]")
                if isinstance(leader_stocks, str):
                    try:
                        leader_stocks = json.loads(leader_stocks)
                    except json.JSONDecodeError:
                        leader_stocks = []
                perf = {}
                for s in leader_stocks:
                    code = s.get("code", "")
                    if code and code in returns:
                        perf[code] = returns[code]
                perf["index_return"] = index_return

                update_prediction_status(client, pred["id"], status, perf)

    print(f"\n  결과: hit={results['hit']}, missed={results['missed']}, "
          f"expired={results['expired']}, active={results['active']}")

    # Step 4: 정확도 리포트
    print("\n[4/4] 정확도 리포트...")
    if not test_mode:
        report = calculate_accuracy_report(client)
        print(f"  전체: {report['hit']}/{report['total']} ({report['accuracy']}%)")
        for conf, data in report.get("by_confidence", {}).items():
            print(f"  신뢰도 {conf}: {data['hit']}/{data['total']} ({data['accuracy']}%)")
        for cat, data in report.get("by_category", {}).items():
            print(f"  카테고리 {cat}: {data['hit']}/{data['total']} ({data['accuracy']}%)")
    else:
        print("  ⏭ 정확도 리포트 건너뜀 (테스트 모드)")

    print("\n" + "=" * 50)
    print("✅ 예측 백테스팅 완료")
    print("=" * 50)


if __name__ == "__main__":
    main()
