import asyncio
import os
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from playwright.async_api import async_playwright

ARTIFACT_DIR = r"C:\Users\HP\.gemini\antigravity\brain\f4297fde-8f77-4c02-ac0c-b30746ddf9cf"
CHART_SCREENSHOT_PATH = os.path.join(ARTIFACT_DIR, "ai_chart_analysis_verified.png")

async def run_vision_test():
    print("Starting Playwright AI Chart Canvas Verification...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1440, "height": 1080})
        page = await context.new_page()

        print("Navigating to http://localhost:8000/ ...")
        await page.goto("http://localhost:8000/", wait_until="networkidle", timeout=60000)

        # Wait for chart canvas wrapper
        print("Waiting for #chartCanvasWrapper...")
        chart_wrapper = await page.wait_for_selector("#chartCanvasWrapper", timeout=30000)
        await page.wait_for_selector("#aiChartFloatingHud", timeout=30000)

        # Scroll into view
        await chart_wrapper.scroll_into_view_if_needed()

        # Wait for #chartLoader to be hidden (meaning /api/analyze completed and rendered)
        print("Waiting for chart data and Groq AI analysis to load (#chartLoader hidden)...")
        await page.wait_for_selector("#chartLoader", state="hidden", timeout=60000)
        print("Chart data loaded! Waiting 3s for canvas overlays to paint...")
        await asyncio.sleep(3)

        hud_title = await page.inner_text("#aiHudTitle")
        hud_sub = await page.inner_text("#aiHudSub")
        print(f"HUD Title: {hud_title.encode('ascii', 'replace').decode()}")
        print(f"HUD Subtitle: {hud_sub.encode('ascii', 'replace').decode()}")

        # Capture element screenshot of the full chart with AI HUD and overlays
        os.makedirs(ARTIFACT_DIR, exist_ok=True)
        await chart_wrapper.screenshot(path=CHART_SCREENSHOT_PATH)
        print(f"OK: Chart element screenshot captured: {CHART_SCREENSHOT_PATH}")

        await browser.close()
        print("Chart Vision Verification complete!")

if __name__ == "__main__":
    asyncio.run(run_vision_test())
