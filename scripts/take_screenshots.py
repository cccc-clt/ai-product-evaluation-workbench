"""Take screenshots of every page in the Streamlit app using Playwright + Edge."""

import subprocess
import sys
import time
from pathlib import Path

import requests
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
IMAGES_DIR = ROOT / "docs" / "images"
IMAGES_DIR.mkdir(parents=True, exist_ok=True)

EDGE_EXE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
BASE_URL = "http://localhost:8502"  # use 8502 to avoid conflicts

PAGES = [
    ("01_home.png",          BASE_URL,                          "首页"),
    ("02_prompt_lab.png",    f"{BASE_URL}/Prompt_实验台",         "Prompt 实验台"),
    ("03_model_compare.png", f"{BASE_URL}/多模型对比",             "多模型对比"),
    ("04_rag_evaluation.png",f"{BASE_URL}/RAG_文档问答评测",       "RAG 评测"),
    ("05_dashboard.png",     f"{BASE_URL}/评测看板",              "评测看板"),
    ("06_advisor.png",       f"{BASE_URL}/AI_优化建议",           "AI 优化建议"),
]

def wait_for_streamlit(timeout=60):
    for _ in range(timeout):
        try:
            r = requests.get(BASE_URL, timeout=2)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(1)
    return False

def main():
    print("Starting Streamlit on port 8502...")
    proc = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", str(ROOT / "app.py"),
         "--server.port", "8502",
         "--server.headless", "true",
         "--browser.gatherUsageStats", "false"],
        cwd=str(ROOT),
    )

    try:
        print("Waiting for Streamlit to be ready...")
        if not wait_for_streamlit():
            print("ERROR: Streamlit did not start in time")
            proc.terminate()
            return

        print("Streamlit is up. Launching Edge...")
        time.sleep(3)  # extra settle time for Streamlit's React boot

        with sync_playwright() as p:
            browser = p.chromium.launch(
                executable_path=EDGE_EXE,
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage"],
            )
            ctx = browser.new_context(
                viewport={"width": 1400, "height": 900},
                locale="zh-CN",
            )
            page = ctx.new_page()

            # ── Seed demo data first via the dashboard page ──────────────
            print("Seeding demo data...")
            page.goto(f"{BASE_URL}/评测看板", wait_until="networkidle", timeout=30000)
            time.sleep(3)
            # Click the seed button if present
            try:
                btn = page.locator("button", has_text="生成 Demo 数据")
                if btn.count() > 0:
                    btn.first.click()
                    time.sleep(3)
                    page.reload(wait_until="networkidle")
                    time.sleep(2)
            except Exception as e:
                print(f"  (seed button not found or already seeded: {e})")

            # ── Capture each page ────────────────────────────────────────
            for filename, url, label in PAGES:
                out = IMAGES_DIR / filename
                print(f"Screenshotting {label} → {out.name}")
                try:
                    page.goto(url, wait_until="networkidle", timeout=30000)
                    # Wait for Streamlit spinner to clear
                    try:
                        page.wait_for_selector("[data-testid='stSpinner']",
                                               state="detached", timeout=10000)
                    except Exception:
                        pass
                    time.sleep(2)
                    page.screenshot(path=str(out), full_page=True)
                    print(f"  ✓ saved {out.name}")
                except Exception as e:
                    print(f"  ✗ {label}: {e}")

            browser.close()

        print("\nAll screenshots done.")
        for filename, _, label in PAGES:
            status = "✓" if (IMAGES_DIR / filename).exists() else "✗"
            print(f"  {status}  {filename}  ({label})")

    finally:
        proc.terminate()
        proc.wait()


if __name__ == "__main__":
    main()
