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
    port = 8092
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
            page = browser.new_page(viewport={"width": 1450, "height": 1000})
            
            print(f"Navigating to http://127.0.0.1:{port}...", flush=True)
            page.goto(f"http://127.0.0.1:{port}", wait_until="domcontentloaded", timeout=25000)
            
            # Wait for master confluence card to be visible
            print("Waiting for #masterConfluenceCard...", flush=True)
            page.wait_for_selector("#masterConfluenceCard", timeout=15000)
            
            # Wait for data to arrive from /api/analyze and populate confluence UI
            print("Waiting for confluence data to populate...", flush=True)
            page.wait_for_function(
                "() => { const el = document.getElementById('confluenceActionText'); return el && el.innerText.trim() !== 'SCANNING'; }",
                timeout=30000
            )

            action_text = page.locator("#confluenceActionText").inner_text()
            accuracy_text = page.locator("#confluenceAccuracyText").inner_text()
            setup_tag = page.locator("#confluenceSetupTag").inner_text()
            rule_title = page.locator("#confluenceRuleTitle").inner_text()
            exec_entry = page.locator("#confExecEntry").inner_text()
            exec_sl = page.locator("#confExecSL").inner_text()
            exec_tp1 = page.locator("#confExecT1").inner_text()

            print(f"Action: {action_text}", flush=True)
            print(f"Accuracy: {accuracy_text}", flush=True)
            print(f"Setup Tag: {setup_tag}", flush=True)
            print(f"Grade: {rule_title}", flush=True)
            print(f"Entry: {exec_entry} | SL: {exec_sl} | TP1: {exec_tp1}", flush=True)

            # Test Tab Switching
            print("Testing Tab 2 (Candlestick & VSA)...", flush=True)
            page.click("#btnTabCandleVsa")
            time.sleep(0.3)
            candle_name = page.locator("#tabCandleName").inner_text()
            vsa_verdict = page.locator("#tabVsaVerdict").inner_text()
            print(f"Tab 2 Candle: {candle_name} | VSA: {vsa_verdict}", flush=True)

            print("Testing Tab 3 (Indicators & Divergence)...", flush=True)
            page.click("#btnTabIndicators")
            time.sleep(0.3)
            vwap_val = page.locator("#tabVwapVal").inner_text()
            rsi_val = page.locator("#tabRsiVal").inner_text()
            print(f"Tab 3 VWAP: {vwap_val} | RSI: {rsi_val}", flush=True)

            print("Testing Tab 4 (Multi-TF Triad)...", flush=True)
            page.click("#btnTabMultiTf")
            time.sleep(0.3)
            triad_sum = page.locator("#tabTriadSummary").inner_text()
            print(f"Tab 4 Triad: {triad_sum}", flush=True)

            print("Testing Tab 5 (Breakout Radar)...", flush=True)
            page.click("#btnTabBreakout")
            time.sleep(0.3)
            radar_setup = page.locator("#tabRadarStageText").inner_text()
            print(f"Tab 5 Radar: {radar_setup}", flush=True)

            # Return to Tab 1
            page.click("#btnTabStructure")
            time.sleep(0.3)

            # Save Dark Theme Screenshot
            artifact_dir = r"C:\Users\HP\.gemini\antigravity\brain\f4297fde-8f77-4c02-ac0c-b30746ddf9cf"
            os.makedirs(artifact_dir, exist_ok=True)
            dark_shot_path = os.path.join(artifact_dir, "confluence_master_verified.png")
            page.screenshot(path=dark_shot_path)
            print(f"Saved dark screenshot to {dark_shot_path}", flush=True)

            # Test Light Theme
            print("Testing light theme toggle...", flush=True)
            page.click("#themeToggleBtn")
            time.sleep(0.5)
            light_shot_path = os.path.join(artifact_dir, "confluence_master_light.png")
            page.screenshot(path=light_shot_path)
            print(f"Saved light screenshot to {light_shot_path}", flush=True)

            # Switch back to dark theme
            page.click("#themeToggleBtn")
            time.sleep(0.3)

            # Test Chart Price Lines Toggle
            print("Testing Chart Levels toggle button...", flush=True)
            page.click("#btnToggleChartLevels")
            time.sleep(0.3)
            levels_btn_text = page.locator("#btnToggleChartLevels").inner_text()
            print(f"Levels button text: {levels_btn_text}", flush=True)

            # Test Confluence Drawer Collapse/Expand
            print("Testing drawer collapse...", flush=True)
            page.click("#confluenceToggleBtn")
            time.sleep(0.3)
            drawer_display = page.evaluate("() => document.getElementById('confluenceDrawer').style.display")
            print(f"Drawer display collapsed: {drawer_display}", flush=True)
            assert drawer_display == "none"

            page.click("#confluenceToggleBtn")
            time.sleep(0.3)
            drawer_display = page.evaluate("() => document.getElementById('confluenceDrawer').style.display")
            print(f"Drawer display expanded: {drawer_display}", flush=True)
            assert drawer_display == "flex"

            # Test Switching Symbol to BTC-USD (Crypto)
            print("Testing symbol switch to BTC-USD (Crypto)...", flush=True)
            page.click("button.symbol-chip:has-text('BTC-USD')")
            time.sleep(3.0)
            page.wait_for_function(
                "() => { const el = document.getElementById('activeSymbolTitle'); return el && el.innerText.includes('BTC-USD'); }",
                timeout=20000
            )
            btc_action = page.locator("#confluenceActionText").inner_text()
            btc_acc = page.locator("#confluenceAccuracyText").inner_text()
            print(f"BTC-USD Confluence Action: {btc_action} | Accuracy: {btc_acc}", flush=True)

            crypto_shot_path = os.path.join(artifact_dir, "confluence_master_crypto.png")
            page.screenshot(path=crypto_shot_path)
            print(f"Saved crypto screenshot to {crypto_shot_path}", flush=True)

            print("ALL PLAYWRIGHT TESTS PASSED SUCCESSFULLY!", flush=True)

    finally:
        print("Stopping uvicorn server...", flush=True)
        server_process.terminate()
        server_process.wait()
        print("Server stopped cleanly.", flush=True)

if __name__ == "__main__":
    run_test()
