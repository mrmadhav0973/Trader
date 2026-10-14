import subprocess
import time
import sys
import os
import urllib.request
import json

# Ensure UTF-8 output on Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from playwright.sync_api import sync_playwright

def wait_for_server(url, timeout=30):
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
    port = 8094
    print(f"Starting uvicorn server on port {port}...", flush=True)
    log_file = open("test_server_ai_output.log", "w", encoding="utf-8")
    server_process = subprocess.Popen(
        [sys.executable, "-u", "-m", "uvicorn", "server:app", "--host", "127.0.0.1", "--port", str(port)],
        stdout=log_file,
        stderr=subprocess.STDOUT,
        cwd=os.path.dirname(os.path.abspath(__file__))
    )
    
    print("Waiting for server to become ready...", flush=True)
    if not wait_for_server(f"http://127.0.0.1:{port}/api/indices", timeout=60):
        server_process.terminate()
        log_file.close()
        with open("test_server_ai_output.log", "r", encoding="utf-8", errors="ignore") as f:
            print("SERVER LOGS:\n" + f.read(), flush=True)
        raise RuntimeError("Server failed to respond within 60 seconds.")
    print("Server is ready and responding!", flush=True)
    time.sleep(2.0)

    try:
        # 1. Test Backend AI Audit Endpoint
        print("Testing GET /api/ai/audit?symbol=TATAPOWER.NS&timeframe=1d...", flush=True)
        audit_url = f"http://127.0.0.1:{port}/api/ai/audit?symbol=TATAPOWER.NS&timeframe=1d"
        req = urllib.request.Request(audit_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            assert resp.status == 200
            audit_data = json.loads(resp.read().decode("utf-8"))
            print(f"AI Audit Verdict: {audit_data.get('verdict_badge')} | Conviction: {audit_data.get('conviction_score')}%", flush=True)
            print(f"AI Headline: {audit_data.get('verdict_headline')}", flush=True)
            assert "desk_verdict" in audit_data
            assert "veteran_rationale" in audit_data

        # 2. Test Backend AI Ask Endpoint
        print("Testing POST /api/ai/ask...", flush=True)
        ask_url = f"http://127.0.0.1:{port}/api/ai/ask"
        payload = json.dumps({
            "symbol": "TATAPOWER.NS",
            "timeframe": "1d",
            "question": "Where are institutional stop-losses clustered?"
        }).encode("utf-8")
        post_req = urllib.request.Request(ask_url, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(post_req, timeout=30) as resp:
            assert resp.status == 200
            ask_data = json.loads(resp.read().decode("utf-8"))
            print(f"AI Answer Preview: {ask_data.get('answer')[:120]}...", flush=True)
            assert len(ask_data.get("answer", "")) > 20

        # 3. Test Frontend UI in Headless Chromium
        with sync_playwright() as p:
            print("Launching Chromium...", flush=True)
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1450, "height": 1100})
            page.on("console", lambda msg: print(f"[BROWSER CONSOLE] {msg.type}: {msg.text}", flush=True))
            page.on("pageerror", lambda err: print(f"[BROWSER ERROR] {err}", flush=True))
            
            print(f"Navigating to http://127.0.0.1:{port}...", flush=True)
            page.goto(f"http://127.0.0.1:{port}", wait_until="domcontentloaded", timeout=25000)
            
            # Wait for AI Veteran Desk Card
            print("Waiting for #aiVeteranDeskCard...", flush=True)
            page.wait_for_selector("#aiVeteranDeskCard", timeout=15000)
            
            # Wait for AI audit to populate
            print("Waiting for AI verdict badge to update...", flush=True)
            page.wait_for_function(
                "() => { const el = document.getElementById('aiDeskVerdictBadge'); return el && !el.innerText.includes('CONSULTING'); }",
                timeout=45000
            )

            badge_text = page.locator("#aiDeskVerdictBadge").inner_text()
            score_text = page.locator("#aiDeskConvictionScore").inner_text()
            headline_text = page.locator("#aiDeskHeadline").inner_text()
            trap_text = page.locator("#aiDeskTrapWarning").inner_text()
            opt_entry = page.locator("#aiDeskOptimalEntry").inner_text()
            smart_sl = page.locator("#aiDeskSmartSL").inner_text()
            print(f"UI AI Badge: {badge_text} | Score: {score_text}", flush=True)
            print(f"UI AI Headline: {headline_text}", flush=True)
            print(f"UI AI Trap Warning: {trap_text[:100]}...", flush=True)
            print(f"UI AI Entry: {opt_entry} | SL: {smart_sl}", flush=True)

            assert len(headline_text) > 10
            assert len(trap_text) > 10

            # Test Quick Chip Chat Interaction
            print("Testing Quick Chip click: '🪤 Is this a retail trap?'...", flush=True)
            page.click("button.ai-chip-btn:has-text('retail trap')")
            time.sleep(1.0)
            
            # Wait for the AI response in chat stream
            print("Waiting for Desk Head answer in chat stream...", flush=True)
            page.wait_for_function(
                "() => { const msgs = document.querySelectorAll('#aiChatStream .ai-msg-veteran'); return msgs.length >= 2; }",
                timeout=45000
            )

            desk_answers = page.locator("#aiChatStream .ai-msg-veteran").all_inner_texts()
            latest_ans = desk_answers[-1]
            print(f"Desk Head Live Answer: {latest_ans[:140]}...", flush=True)
            assert len(latest_ans) > 30

            # Screenshot AI Veteran Desk Card
            artifact_dir = r"C:\Users\HP\.gemini\antigravity\brain\f4297fde-8f77-4c02-ac0c-b30746ddf9cf"
            os.makedirs(artifact_dir, exist_ok=True)
            shot_path = os.path.join(artifact_dir, "ai_veteran_desk_verified.png")
            page.locator("#aiVeteranDeskCard").screenshot(path=shot_path)
            print(f"Saved AI Veteran Desk screenshot to {shot_path}", flush=True)

            print("ALL AI VETERAN DESK TESTS PASSED SUCCESSFULLY!", flush=True)

    finally:
        print("Stopping server...", flush=True)
        try:
            log_file.close()
        except Exception:
            pass
        server_process.terminate()
        server_process.wait()
        print("Server stopped cleanly.", flush=True)

if __name__ == "__main__":
    run_test()
