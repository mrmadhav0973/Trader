import subprocess
import time
import sys
import os
import urllib.request

# Ensure UTF-8 output on Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from playwright.sync_api import sync_playwright

def wait_for_server(url, timeout=20):
    start = time.time()
    while time.time() - start < timeout:
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                if response.status == 200:
                    return True
        except Exception:
            time.sleep(0.5)
    return False

def run_test():
    port = 8090
    print(f"Starting uvicorn server on port {port}...", flush=True)
    server_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "server:app", "--host", "127.0.0.1", "--port", str(port)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        cwd=os.path.dirname(os.path.abspath(__file__))
    )
    
    print("Waiting for server to become ready...", flush=True)
    if not wait_for_server(f"http://127.0.0.1:{port}/api/indices", timeout=20):
        server_process.terminate()
        raise RuntimeError("Server failed to respond within 20 seconds.")
    print("Server is ready and responding!", flush=True)

    try:
        with sync_playwright() as p:
            print("Launching Chromium...", flush=True)
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1400, "height": 950})
            
            print(f"Navigating to http://127.0.0.1:{port}...", flush=True)
            page.goto(f"http://127.0.0.1:{port}", wait_until="domcontentloaded", timeout=20000)
            
            # Wait for chart and breakout radar to load
            print("Waiting for breakout radar card...", flush=True)
            page.wait_for_selector("#breakoutRadarCard", timeout=15000)
            
            # Wait for data to arrive from /api/analyze
            print("Waiting for radar setup data...", flush=True)
            page.wait_for_function(
                "() => document.getElementById('radarStageText') && document.getElementById('radarStageText').innerText !== '👀 SCANNING STRUCTURE'",
                timeout=25000
            )

            setup_text = page.locator("#radarSetupTag").inner_text()
            stage_text = page.locator("#radarStageText").inner_text()
            score_text = page.locator("#radarScoreText").inner_text()
            key_level_text = page.locator("#radarKeyLevel").inner_text()
            entry_text = page.locator("#radarEntryPrice").inner_text()
            rule_text = page.locator("#radarActionAdvice").inner_text()

            print(f"Setup Tag: {setup_text}", flush=True)
            print(f"Stage: {stage_text}", flush=True)
            print(f"Score: {score_text}", flush=True)
            print(f"Key Level: {key_level_text}", flush=True)
            print(f"Entry: {entry_text}", flush=True)
            print(f"Rule: {rule_text[:80]}...", flush=True)

            # Capture screenshot
            artifact_dir = r"C:\Users\HP\.gemini\antigravity\brain\f4297fde-8f77-4c02-ac0c-b30746ddf9cf"
            os.makedirs(artifact_dir, exist_ok=True)
            shot_path = os.path.join(artifact_dir, "breakout_radar_verified.png")
            page.screenshot(path=shot_path)
            print(f"Saved screenshot to {shot_path}", flush=True)

            # Test Collapsing drawer
            print("Testing drawer collapse...", flush=True)
            page.click("#radarToggleBtn")
            time.sleep(0.4)
            drawer_display = page.evaluate("() => document.getElementById('radarDrawer').style.display")
            print(f"Drawer display after collapse toggle: {drawer_display}", flush=True)
            assert drawer_display == "none", f"Expected none but got {drawer_display}"

            # Test Expanding drawer
            page.click("#radarToggleBtn")
            time.sleep(0.4)
            drawer_display = page.evaluate("() => document.getElementById('radarDrawer').style.display")
            print(f"Drawer display after expand toggle: {drawer_display}", flush=True)
            assert drawer_display == "flex", f"Expected flex but got {drawer_display}"

            # Test Toggle Radar Visibility
            print("Testing radar visibility button...", flush=True)
            page.click("#btnToggleRadar")
            time.sleep(0.4)
            card_display = page.evaluate("() => document.getElementById('breakoutRadarCard').style.display")
            btn_text = page.locator("#btnToggleRadar").inner_text()
            print(f"Radar card display after off toggle: {card_display}, button: {btn_text}", flush=True)
            assert card_display == "none", f"Expected none but got {card_display}"
            assert "OFF" in btn_text, f"Expected OFF in button text but got {btn_text}"

            # Turn back on
            page.click("#btnToggleRadar")
            time.sleep(0.4)
            card_display = page.evaluate("() => document.getElementById('breakoutRadarCard').style.display")
            btn_text = page.locator("#btnToggleRadar").inner_text()
            print(f"Radar card display after on toggle: {card_display}, button: {btn_text}", flush=True)
            assert card_display == "flex", f"Expected flex but got {card_display}"
            assert "ON" in btn_text, f"Expected ON in button text but got {btn_text}"

            # Test Light Theme
            print("Testing Light Theme...", flush=True)
            page.click("#themeToggleBtn")
            time.sleep(0.8)
            shot_light_path = os.path.join(artifact_dir, "breakout_radar_light.png")
            page.screenshot(path=shot_light_path)
            print(f"Saved light theme screenshot to {shot_light_path}", flush=True)

            browser.close()
            print("ALL BREAKOUT RADAR TESTS PASSED SUCCESSFULLY!", flush=True)
    finally:
        server_process.terminate()
        server_process.wait()

if __name__ == "__main__":
    run_test()
