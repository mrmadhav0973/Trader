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
    port = 8098
    print(f"Starting uvicorn server on port {port}...", flush=True)
    log_file = open("test_server_output.log", "w", encoding="utf-8")
    server_process = subprocess.Popen(
        [sys.executable, "-u", "-m", "uvicorn", "server:app", "--host", "127.0.0.1", "--port", str(port)],
        stdout=log_file,
        stderr=subprocess.STDOUT,
        cwd=os.path.dirname(os.path.abspath(__file__))
    )
    
    print("Waiting for server to become ready...", flush=True)
    if not wait_for_server(f"http://127.0.0.1:{port}/", timeout=60):
        server_process.terminate()
        log_file.close()
        with open("test_server_output.log", "r", encoding="utf-8", errors="ignore") as f:
            print("SERVER LOGS:\n" + f.read(), flush=True)
        raise RuntimeError("Server failed to respond within 60 seconds.")
    print("Server is ready and responding!", flush=True)

    try:
        with sync_playwright() as p:
            print("Launching Chromium...", flush=True)
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1450, "height": 1000})
            page.on("console", lambda msg: print(f"[BROWSER CONSOLE] {msg.type}: {msg.text}", flush=True))
            page.on("pageerror", lambda err: print(f"[BROWSER ERROR] {err}", flush=True))
            
            print(f"Navigating to http://127.0.0.1:{port}...", flush=True)
            page.goto(f"http://127.0.0.1:{port}", wait_until="domcontentloaded", timeout=25000)
            
            # Wait for master confluence card to be visible
            print("Waiting for #masterConfluenceCard...", flush=True)
            page.wait_for_selector("#masterConfluenceCard", timeout=15000)
            
            # Wait for data to arrive from /api/analyze and populate confluence UI
            print("Waiting for confluence data to populate...", flush=True)
            page.wait_for_function(
                "() => { const el = document.getElementById('confluenceActionText'); return el && el.innerText.trim() !== 'SCANNING'; }",
                timeout=45000
            )

            action_text = page.locator("#confluenceActionText").inner_text()
            accuracy_text = page.locator("#confluenceAccuracyText").inner_text()
            setup_tag = page.locator("#confluenceSetupTag").inner_text()
            rule_title = page.locator("#confluenceRuleTitle").inner_text()
            exec_entry = page.locator("#confExecEntry").inner_text()
            exec_sl = page.locator("#confExecSL").inner_text()
            exec_tp1 = page.locator("#confExecT1").inner_text()
            exec_tp2 = page.locator("#confExecT2").inner_text()
            exec_tp3 = page.locator("#confExecT3").inner_text()
            adr_badge = page.locator("#confAdrBadge").inner_text()
            entry_pill = page.locator("#confEntryTypePill").inner_text()
            sl_pill = page.locator("#confSlBufferPill").inner_text()
            trade_mgmt = page.locator("#confTradeMgmtText").inner_text()

            print(f"Action: {action_text}", flush=True)
            print(f"Accuracy: {accuracy_text}", flush=True)
            print(f"Setup Tag: {setup_tag}", flush=True)
            print(f"Grade: {rule_title}", flush=True)
            print(f"Entry ({entry_pill}): {exec_entry} | SL ({sl_pill}): {exec_sl}", flush=True)
            print(f"TP Ladder -> TP1: {exec_tp1} | TP2: {exec_tp2} | TP3: {exec_tp3}", flush=True)
            print(f"ADR Badge: {adr_badge}", flush=True)
            print(f"Trade Management: {trade_mgmt}", flush=True)

            assert len(exec_tp1) > 1, "TP1 missing"
            assert len(exec_tp2) > 1, "TP2 missing"
            assert len(exec_tp3) > 1, "TP3 missing"
            assert len(adr_badge) > 5, "ADR feasibility badge missing"
            assert len(entry_pill) >= 3, "Entry pill missing"
            assert len(sl_pill) >= 3, "Anti-hunt buffer pill missing"

            # Test Copy Bracket Order Button
            print("Testing 'Copy Bracket Order' button...", flush=True)
            page.click("#btnCopyConfluenceOrder")
            time.sleep(0.3)
            toast_text = page.locator("#statusToast").inner_text()
            print(f"Toast Notification: {toast_text}", flush=True)

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

            # Test Tab 6: 8 Advanced Institutional Confluences
            print("Testing Tab 6 (8 Advanced Confluences)...", flush=True)
            page.click("#btnTabInstitutional")
            time.sleep(0.4)
            fvg_val = page.locator("#tabFvgVal").inner_text()
            rs_val = page.locator("#tabRsVal").inner_text()
            fib_val = page.locator("#tabFibVal").inner_text()
            kz_val = page.locator("#tabKillzoneVal").inner_text()
            oi_val = page.locator("#tabOiVal").inner_text()
            ttm_val = page.locator("#tabTtmVal").inner_text()
            vix_val = page.locator("#tabVixVal").inner_text()
            cvd_val = page.locator("#tabCvdVal").inner_text()

            print(f"1. FVG: {fvg_val}", flush=True)
            print(f"2. RS/RW: {rs_val}", flush=True)
            print(f"3. Fib Golden Pocket: {fib_val}", flush=True)
            print(f"4. Killzone: {kz_val}", flush=True)
            print(f"5. OI/PCR: {oi_val}", flush=True)
            print(f"6. TTM Squeeze: {ttm_val}", flush=True)
            print(f"7. India VIX: {vix_val}", flush=True)
            print(f"8. CVD: {cvd_val}", flush=True)

            assert len(fvg_val) > 2, "FVG value missing"
            assert len(rs_val) > 2, "RS/RW value missing"
            assert len(fib_val) > 2, "Fib value missing"
            assert len(kz_val) > 2, "Killzone value missing"
            assert len(oi_val) > 2, "OI/PCR value missing"
            assert len(ttm_val) > 2, "TTM value missing"
            assert len(vix_val) > 2, "VIX value missing"
            assert len(cvd_val) > 2, "CVD value missing"

            # Save screenshot of 8 Advanced Confluences tab
            artifact_dir = r"C:\Users\HP\.gemini\antigravity\brain\f4297fde-8f77-4c02-ac0c-b30746ddf9cf"
            os.makedirs(artifact_dir, exist_ok=True)
            adv_shot_path = os.path.join(artifact_dir, "advanced_confluences_suite.png")
            page.screenshot(path=adv_shot_path)
            print(f"Saved advanced confluences screenshot to {adv_shot_path}", flush=True)

            # Return to Tab 1
            page.click("#btnTabStructure")
            time.sleep(0.3)

            # Save Dark Theme Screenshot
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

            # Verify Chart Visual Analysis Overlays
            print("Verifying Chart Visual Analysis Elements...", flush=True)
            canvas_exists = page.evaluate("() => !!document.getElementById('tvZonesCanvas')")
            print(f"S/R Canvas Overlay exists: {canvas_exists}", flush=True)
            assert canvas_exists, "tvZonesCanvas element missing"

            # Check indicator series data
            has_emas = page.evaluate("() => !!tvEma20Series && !!tvEma50Series && !!tvEma200Series")
            print(f"EMA 20/50/200 series initialized: {has_emas}", flush=True)
            assert has_emas, "EMA series not initialized"

            has_vwap = page.evaluate("() => !!tvVwapSeries")
            print(f"VWAP series initialized: {has_vwap}", flush=True)
            assert has_vwap, "VWAP series not initialized"

            # Test Chart Overlay Toggle Buttons
            print("Testing Zones Toggle...", flush=True)
            page.click("#btnToggleZones")
            time.sleep(0.2)
            z_text = page.locator("#btnToggleZones").inner_text()
            print(f"Zones Toggle text: {z_text}", flush=True)
            assert "OFF" in z_text
            page.click("#btnToggleZones")
            time.sleep(0.2)

            print("Testing FVG Toggle...", flush=True)
            page.click("#btnToggleFvg")
            time.sleep(0.2)
            fvg_btn_text = page.locator("#btnToggleFvg").inner_text()
            print(f"FVG Toggle text: {fvg_btn_text}", flush=True)
            assert "OFF" in fvg_btn_text
            page.click("#btnToggleFvg")
            time.sleep(0.2)

            print("Testing Fib OTE Toggle...", flush=True)
            page.click("#btnToggleFib")
            time.sleep(0.2)
            fib_btn_text = page.locator("#btnToggleFib").inner_text()
            print(f"Fib OTE Toggle text: {fib_btn_text}", flush=True)
            assert "OFF" in fib_btn_text
            page.click("#btnToggleFib")
            time.sleep(0.2)

            print("Testing EMAs Toggle...", flush=True)
            page.click("#btnToggleEmas")
            time.sleep(0.2)
            ema_text = page.locator("#btnToggleEmas").inner_text()
            print(f"EMAs Toggle text: {ema_text}", flush=True)
            assert "OFF" in ema_text
            page.click("#btnToggleEmas")
            time.sleep(0.2)

            # Test Chart Price Lines Toggle
            print("Testing Chart Levels toggle button...", flush=True)
            page.click("#btnToggleChartLevels")
            time.sleep(0.3)
            levels_btn_text = page.locator("#btnToggleChartLevels").inner_text()
            print(f"Levels button text: {levels_btn_text}", flush=True)
            page.click("#btnToggleChartLevels")
            time.sleep(0.3)

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
            page.evaluate("() => selectSymbol('BTC-USD')")
            time.sleep(2.0)
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

            # =================================================================
            # Test Institutional Market Screener Block
            # =================================================================
            print("\n--- TESTING INSTITUTIONAL MARKET SCREENER ---", flush=True)
            screener_sec = page.locator("#marketScreenerSection")
            assert screener_sec.is_visible()
            print("Market screener section is visible!", flush=True)

            print("Waiting for screener table to populate with setups...", flush=True)
            page.wait_for_function(
                "() => { const rows = document.querySelectorAll('#screenerTableBody tr.screener-row'); return rows.length > 0; }",
                timeout=35000
            )

            row_count = page.evaluate("() => document.querySelectorAll('#screenerTableBody tr.screener-row').length")
            print(f"Screener table populated with {row_count} setups!", flush=True)
            assert row_count > 0, "Expected at least 1 setup in screener"

            # Check confluence score formatting on first row
            first_score_text = page.locator("#screenerTableBody tr.screener-row .screener-score-pill").first.inner_text()
            print(f"First setup confluence score pill: {first_score_text}", flush=True)
            assert "%" in first_score_text and "Pillars" in first_score_text

            # Test local search filter and loading via "Analyze ↗"
            print("Testing local search filter input with 'TATA'...", flush=True)
            page.fill("#screenerSearchInput", "TATA")
            time.sleep(0.5)
            filtered_count = page.evaluate("() => document.querySelectorAll('#screenerTableBody tr.screener-row').length")
            print(f"Filtered by 'TATA': {filtered_count} setups", flush=True)
            assert filtered_count >= 1

            # Test jumping/loading a symbol into the chart terminal via "Analyze ↗"
            print("Testing 'Analyze ↗' button navigation on TATAPOWER...", flush=True)
            analyze_btn = page.locator("#screenerTableBody tr.screener-row .btn-screener-load").first
            analyze_btn.click(force=True)
            target_token = "TATAPOWER"
            print(f"Waiting for chart title to include '{target_token}'...", flush=True)
            page.wait_for_function(
                f"() => {{ const el = document.getElementById('activeSymbolTitle'); return el && el.innerText.includes('{target_token}'); }}",
                timeout=25000
            )
            active_title = page.locator("#activeSymbolTitle").inner_text()
            print(f"Active symbol title after screener click: {active_title}", flush=True)

            # Clear search input for category test
            page.fill("#screenerSearchInput", "")
            time.sleep(0.4)

            # Test Quick Category Filter Pill (Crypto 24/7)
            print("Testing Category filter pill ('Crypto 24/7')...", flush=True)
            page.click("button.screener-pill-btn:has-text('Crypto 24/7')")
            time.sleep(1.0)
            page.wait_for_function(
                "() => { const rows = document.querySelectorAll('#screenerTableBody tr.screener-row'); const l = document.getElementById('screenerLoader'); return rows.length > 0 && (!l || l.style.display === 'none'); }",
                timeout=30000
            )
            time.sleep(0.5)
            crypto_rows = page.evaluate("() => document.querySelectorAll('#screenerTableBody tr.screener-row').length")
            print(f"Crypto filtered setups count: {crypto_rows}", flush=True)
            assert crypto_rows > 0

            # Capture screenshot of full market screener
            screener_shot_path = os.path.join(artifact_dir, "market_screener_verified.png")
            page.locator("#marketScreenerSection").screenshot(path=screener_shot_path)
            print(f"Saved market screener screenshot to {screener_shot_path}", flush=True)

            print("ALL PLAYWRIGHT TESTS PASSED SUCCESSFULLY!", flush=True)

    finally:
        print("Stopping uvicorn server...", flush=True)
        try:
            log_file.close()
        except Exception:
            pass
        server_process.terminate()
        server_process.wait()
        print("Server stopped cleanly.", flush=True)

if __name__ == "__main__":
    run_test()
