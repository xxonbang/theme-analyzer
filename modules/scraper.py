"""
Playwright 기반 리스트 수집 및 스크린샷 캡처 (신버전 stock.naver.com)
"""
from __future__ import annotations
import asyncio
from datetime import datetime, timezone, timedelta
from pathlib import Path
from playwright.async_api import async_playwright, Page

# KST 시간대
KST = timezone(timedelta(hours=9))

from config.settings import (
    KOSPI_API_URL,
    KOSDAQ_API_URL,
    STOCK_DETAIL_URL,
    MAX_KOSPI_STOCKS,
    MAX_KOSDAQ_STOCKS,
    VIEWPORT_WIDTH,
    VIEWPORT_HEIGHT,
    DEVICE_SCALE_FACTOR,
    USER_AGENT,
    CAPTURES_DIR,
)
from modules.utils import get_today_capture_dir


async def fetch_stock_list_from_api(page: Page, api_url: str, market: str, max_stocks: int) -> list[dict]:
    """신버전 API에서 거래량 상위 종목 리스트 추출"""
    print(f"[{market}] API 호출: {api_url[:80]}...")

    response = await page.goto(api_url)
    data = await response.json()

    stocks = []
    for item in data[:max_stocks]:
        stocks.append({
            "code": item.get("itemcode"),
            "name": item.get("itemname"),
            "market": market
        })

    print(f"[{market}] {len(stocks)}개 종목 수집 완료")
    return stocks


async def collect_all_stocks() -> list[dict]:
    """코스피 50개 + 코스닥 70개 = 총 120개 종목 수집 (API 방식)"""
    print("\n=== Phase 1: 종목 리스트 수집 (신버전 API) ===\n")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        kospi = await fetch_stock_list_from_api(page, KOSPI_API_URL, "코스피", MAX_KOSPI_STOCKS)
        kosdaq = await fetch_stock_list_from_api(page, KOSDAQ_API_URL, "코스닥", MAX_KOSDAQ_STOCKS)

        await browser.close()

    all_stocks = kospi + kosdaq
    print(f"\n총 {len(all_stocks)}개 종목 수집 완료 (코스피 {len(kospi)}개 + 코스닥 {len(kosdaq)}개)")
    return all_stocks


async def click_more_buttons(page: Page):
    """'더보기' 링크들을 클릭하여 추가 정보 표시"""
    # 종목 정보 더보기 클릭 (a 태그)
    try:
        stock_info_link = page.locator('a:has-text("종목 정보 더보기")')
        if await stock_info_link.count() > 0:
            await stock_info_link.first.click()
            await page.wait_for_timeout(500)
            print("    [클릭] 종목 정보 더보기")
    except Exception:
        pass  # 조용히 스킵

    # 매매동향 더보기 클릭 (a 태그)
    try:
        trading_link = page.locator('a:has-text("매매동향 더보기")')
        if await trading_link.count() > 0:
            await trading_link.first.click()
            await page.wait_for_timeout(500)
            print("    [클릭] 매매동향 더보기")
    except Exception:
        pass  # 조용히 스킵


async def capture_stock_screenshot(page: Page, stock: dict, capture_dir: Path, max_retries: int = 2) -> dict:
    """개별 종목 페이지 스크린샷 캡처 (태블릿 버전, 더보기 확장, 매매동향까지 포함)"""
    from PIL import Image
    import io

    code = stock["code"]
    name = stock["name"]
    url = STOCK_DETAIL_URL.format(code=code)

    for attempt in range(max_retries):
        try:
            # domcontentloaded로 변경 (networkidle보다 빠름)
            await page.goto(url, wait_until="domcontentloaded", timeout=45000)
            await page.wait_for_timeout(1500)

            # 1. 페이지 스크롤하여 콘텐츠 로딩 (간소화)
            await page.evaluate("""
                async () => {
                    await new Promise(resolve => {
                        let total = 0;
                        const distance = 800;
                        const timer = setInterval(() => {
                            window.scrollBy(0, distance);
                            total += distance;
                            if (total >= document.body.scrollHeight) {
                                clearInterval(timer);
                                resolve();
                            }
                        }, 80);
                    });
                }
            """)
            await page.wait_for_timeout(800)

            # 2. 스크롤을 맨 위로 복귀
            await page.evaluate("window.scrollTo(0, 0)")
            await page.wait_for_timeout(300)

            # 3. 더보기 링크들 클릭 (종목 정보, 매매동향)
            await click_more_buttons(page)
            await page.wait_for_timeout(1000)

            # 4. 매매동향 더보기 링크 위치 찾기 (캡처 범위 결정)
            capture_height = await page.evaluate("""
                () => {
                    // "매매동향 더보기" 링크 찾기
                    const allLinks = Array.from(document.querySelectorAll('a'));
                    const tradingMoreLink = allLinks.find(a =>
                        a.textContent && a.textContent.includes('매매동향 더보기')
                    );

                    if (tradingMoreLink) {
                        const rect = tradingMoreLink.getBoundingClientRect();
                        // 매매동향 더보기 링크 + 50px 여유
                        return Math.floor(rect.bottom + window.scrollY + 50);
                    }

                    // 못 찾으면 전체 높이의 35%
                    return Math.floor(document.body.scrollHeight * 0.35);
                }
            """)

            # 최소/최대 높이 제한
            capture_height = max(2000, min(capture_height, 4000))

            # 5. sticky 헤더 숨기기 (스크롤 시 나타나는 종목명/가격 헤더)
            await page.evaluate("""
                () => {
                    // sticky 헤더 숨기기
                    const stickyHeaders = document.querySelectorAll('[class*="MainHeader_stockName"], [class*="MainHeader_inner"]');
                    stickyHeaders.forEach(el => {
                        el.style.display = 'none';
                    });

                    // 혹시 다른 sticky/fixed 요소도 숨기기
                    document.querySelectorAll('[class*="sticky"], [class*="Sticky"], [class*="fixed"], [class*="Fixed"]').forEach(el => {
                        const rect = el.getBoundingClientRect();
                        if (rect.top >= 0 && rect.top < 100 && rect.height < 100) {
                            el.style.visibility = 'hidden';
                        }
                    });
                }
            """)
            await page.wait_for_timeout(300)

            # 6. 전체 페이지 스크린샷 (바이트로)
            screenshot_bytes = await page.screenshot(full_page=True)

            # 6. PIL로 이미지 크롭 (매매동향까지만)
            img = Image.open(io.BytesIO(screenshot_bytes))
            img_width, img_height = img.size

            # 실제 캡처 높이 (device_scale_factor 고려)
            actual_capture_height = min(capture_height * DEVICE_SCALE_FACTOR, img_height)

            # 이미지 크롭
            cropped_img = img.crop((0, 0, img_width, actual_capture_height))

            # 저장
            filepath = capture_dir / f"{code}.png"
            cropped_img.save(str(filepath))

            # 캡처 시각 기록 (KST)
            capture_time = datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S")

            print(f"  [OK] {name} ({code}) - {capture_height}px")
            return {**stock, "success": True, "screenshot": str(filepath), "capture_time": capture_time}

        except Exception as e:
            if attempt < max_retries - 1:
                print(f"  [RETRY {attempt + 1}/{max_retries}] {name} ({code})")
                await asyncio.sleep(1)
                continue
            print(f"  [FAIL] {name} ({code})")
            return {**stock, "success": False, "error": str(e)}

    return {**stock, "success": False, "error": "Max retries exceeded"}


async def capture_all_screenshots(stocks: list[dict]) -> list[dict]:
    """모든 종목 스크린샷 캡처"""
    print("\n=== Phase 2: 스크린샷 캡처 ===\n")

    capture_dir = get_today_capture_dir(CAPTURES_DIR)
    print(f"저장 경로: {capture_dir}\n")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": VIEWPORT_WIDTH, "height": VIEWPORT_HEIGHT},
            device_scale_factor=DEVICE_SCALE_FACTOR,
            user_agent=USER_AGENT
        )
        page = await context.new_page()

        results = []
        for i, stock in enumerate(stocks, 1):
            print(f"[{i}/{len(stocks)}]", end="")
            result = await capture_stock_screenshot(page, stock, capture_dir)
            results.append(result)

        await browser.close()

    success = sum(1 for r in results if r.get("success"))
    print(f"\n캡처 완료: 성공 {success}, 실패 {len(results) - success}")

    return results


async def run_scraper(stocks: list[dict] = None) -> list[dict]:
    """스크래퍼 메인 실행"""
    if stocks is None:
        stocks = await collect_all_stocks()

    results = await capture_all_screenshots(stocks)
    return results


# 하위 호환성을 위한 별칭
async def collect_top100_stocks() -> list[dict]:
    """collect_all_stocks의 별칭 (하위 호환성)"""
    return await collect_all_stocks()


if __name__ == "__main__":
    asyncio.run(run_scraper())
