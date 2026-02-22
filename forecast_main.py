"""
유망 테마 예측 — 메인 실행 스크립트

장 개장 전(7:30 AM) 실행하여 전일 데이터 기반으로 유망 테마를 예측합니다.
GitHub Actions cron 또는 수동 실행으로 트리거됩니다.

Usage:
    python forecast_main.py              # 전체 실행
    python forecast_main.py --test       # 테스트 (Supabase 저장 건너뜀)
    python forecast_main.py --intraday   # 장중 재예측 (today만)
"""
import json
import sys
from pathlib import Path

from config.settings import *  # noqa: F401,F403 — 환경변수 로드
from modules.theme_forecast import (
    load_theme_history,
    generate_forecast,
    save_forecast_to_supabase,
    export_forecast_json,
)
from modules.us_market_data import (
    fetch_us_market_data,
    fetch_vix_index,
    fetch_global_market_news,
    calculate_theme_momentum,
)

ROOT_DIR = Path(__file__).parent
DATA_DIR = ROOT_DIR / "frontend" / "public" / "data"


def main():
    test_mode = "--test" in sys.argv
    intraday_mode = "--intraday" in sys.argv

    if test_mode:
        print("🧪 테스트 모드 (Supabase 저장 건너뜀)")
    if intraday_mode:
        print("🔄 장중 재예측 모드 (today만 갱신)")

    print("=" * 50)
    print("📊 유망 테마 예측 시작")
    print("=" * 50)

    # Step 1: 전일 latest.json 로드
    print("\n[1/6] 전일 데이터 로드...")
    latest_path = DATA_DIR / "latest.json"
    if not latest_path.exists():
        print("  ✗ latest.json 파일이 없습니다")
        sys.exit(1)

    with open(latest_path, "r", encoding="utf-8") as f:
        latest_data = json.load(f)

    timestamp = latest_data.get("timestamp", "N/A")
    theme_count = len(latest_data.get("theme_analysis", {}).get("themes", []))
    print(f"  ✓ 전일 데이터 로드 완료 (수집일: {timestamp}, 테마 {theme_count}개)")

    # Step 2: 미국 시장 데이터 + 심리지표 수집
    print("\n[2/6] 미국 시장 데이터 + 심리지표 수집...")
    us_data = fetch_us_market_data()
    if us_data:
        print(f"  ✓ US 시장 데이터 수집 완료 ({len(us_data)}개 지표)")
        for name, info in us_data.items():
            print(f"    - {name}: {info['change_pct']:+.2f}%")
    else:
        print("  ⚠ US 시장 데이터 수집 실패 (계속 진행)")

    sentiment_data = fetch_vix_index()
    if sentiment_data:
        print(f"  ✓ VIX 공포지수: {sentiment_data['score']} ({sentiment_data['rating']})")
    else:
        print("  ⚠ VIX 지수 수집 실패 (계속 진행)")

    global_news = fetch_global_market_news()
    if global_news:
        print(f"  ✓ 글로벌 뉴스 수집 완료 ({len(global_news)}건)")
        for n in global_news[:3]:
            print(f"    - [{n.get('source')}] {n.get('headline', '')[:60]}")
    else:
        print("  ⚠ 글로벌 뉴스 수집 실패 (계속 진행)")

    # Step 3: 테마 히스토리 + 모멘텀 분석
    print("\n[3/6] 테마 히스토리 + 모멘텀 분석...")
    history_dir = DATA_DIR / "history"
    theme_history = load_theme_history(history_dir, days=7)
    print(f"  ✓ 최근 {len(theme_history)}일분 테마 히스토리 로드")

    for entry in theme_history:
        theme_names = [t.get("theme_name", "") for t in entry.get("themes", [])]
        print(f"    - {entry['date']}: {', '.join(theme_names)}")

    momentum_scores = calculate_theme_momentum(theme_history)
    if momentum_scores:
        print(f"  ✓ 모멘텀 분석 완료 ({len(momentum_scores)}개 테마)")
        for m in momentum_scores[:5]:
            print(f"    - {m['theme_name']}: {m['score']:.3f} (등장 {m['frequency']}일)")
    else:
        print("  ⚠ 모멘텀 분석 데이터 없음")

    # Step 4: 섹터 로테이션 분석
    print("\n[4/6] 섹터 로테이션 분석...")
    rotation_data = None
    try:
        from modules.sector_rotation import detect_sector_rotation
        rotation_data = detect_sector_rotation(theme_history, latest_data)
        if rotation_data:
            print(f"  ✓ 섹터 로테이션 분석 완료 ({len(rotation_data)}개 테마)")
            for r in rotation_data[:5]:
                print(f"    - {r['theme_name']}: {r['phase']} ({r['signal']})")
        else:
            print("  ⚠ 섹터 로테이션 데이터 없음")
    except ImportError:
        print("  ⏭ 섹터 로테이션 모듈 미설치 (건너뜀)")

    # Step 5: Gemini 유망 테마 예측
    print("\n[5/6] Gemini 유망 테마 예측...")
    forecast = generate_forecast(
        latest_data, theme_history,
        us_data=us_data,
        sentiment_data=sentiment_data,
        momentum_scores=momentum_scores,
        rotation_data=rotation_data,
        global_news=global_news,
        intraday=intraday_mode,
    )

    if not forecast:
        print("  ✗ 예측 실패")
        sys.exit(1)

    today_count = len(forecast.get("today", []))
    short_count = len(forecast.get("short_term", []))
    long_count = len(forecast.get("long_term", []))
    print(f"  ✓ 예측 완료: 오늘 {today_count}개, 단기 {short_count}개, 장기 {long_count}개")

    # 예측 결과 콘솔 출력
    print("\n  --- 오늘의 유망 테마 ---")
    for t in forecast.get("today", []):
        leaders = ", ".join(s.get("name", "") for s in t.get("leader_stocks", []))
        print(f"  [{t.get('confidence', '')}] {t.get('theme_name', '')} — {t.get('catalyst', '')}")
        print(f"    대장주: {leaders}")

    if not intraday_mode:
        print("\n  --- 단기 유망 테마 (7일 이내) ---")
        for t in forecast.get("short_term", []):
            leaders = ", ".join(s.get("name", "") for s in t.get("leader_stocks", []))
            print(f"  [{t.get('confidence', '')}] {t.get('theme_name', '')} ({t.get('target_period', '')}) — {t.get('catalyst', '')}")
            print(f"    대장주: {leaders}")

        print("\n  --- 장기 유망 테마 (1개월 이내) ---")
        for t in forecast.get("long_term", []):
            leaders = ", ".join(s.get("name", "") for s in t.get("leader_stocks", []))
            print(f"  [{t.get('confidence', '')}] {t.get('theme_name', '')} ({t.get('target_period', '')}) — {t.get('catalyst', '')}")
            print(f"    대장주: {leaders}")

    # Step 6: 저장
    print("\n[6/6] 결과 저장...")

    if intraday_mode:
        # 장중 모드: today 섹션만 갱신
        forecast_path = DATA_DIR / "theme-forecast.json"
        if forecast_path.exists():
            with open(forecast_path, "r", encoding="utf-8") as f:
                existing = json.load(f)
            existing["today"] = forecast["today"]
            existing["market_context"] = forecast["market_context"]
            existing["us_market_summary"] = forecast["us_market_summary"]
            existing["generated_at"] = forecast["generated_at"]
            export_forecast_json(existing)
        else:
            export_forecast_json(forecast)

        if not test_mode:
            # Supabase: today 예측 UPSERT (save_forecast_to_supabase가 UPSERT 처리)
            try:
                today_only = {**forecast, "short_term": [], "long_term": []}
                save_forecast_to_supabase(today_only)
            except Exception as e:
                print(f"  ⚠ Supabase 장중 업데이트 실패: {e}")
        else:
            print("  ⏭ Supabase 저장 건너뜀 (테스트 모드)")
    else:
        # 전체 모드
        export_forecast_json(forecast)
        if not test_mode:
            save_forecast_to_supabase(forecast)
        else:
            print("  ⏭ Supabase 저장 건너뜀 (테스트 모드)")

    print("\n" + "=" * 50)
    print("✅ 유망 테마 예측 완료")
    print("=" * 50)


if __name__ == "__main__":
    main()
