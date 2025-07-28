"""
ChatGPT Selenium collector → market_snapshot.json (sentiment branch)
rev. 2025-07-24

Requires:
    pip install selenium
"""

from pathlib import Path
from datetime import datetime, timedelta, timezone
import json, time, traceback

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
# ────────────────────────────────
# USER CONFIG
# ────────────────────────────────
CHROMEDRIVER = r"C:\chrome-data\chromedriver.exe"
USER_DATA    = r"C:\chrome-data\user-profile"
PROFILE_NAME = "Default"
chatgpt_url  = "https://chatgpt.com/?model=o3"

START_DATE   = "2018-01-01"
END_DATE     = "2018-01-02"
DAY_PAUSE    = 15        # seconds between consecutive dates

SNAPSHOT_ROOT = Path(r"C:\Users\dkdlt\db\db_train\Trend Analyst\daily_snapshots")
LOOP_NAME     = "loop1"
EPISODE_NAME  = "episode13"

# Timing
STABLE_SEC    = 60
POST_WAIT     = 15
RESP_MAX_SEC  = 480

# ────────────────────────────────
# Selenium setup
# ────────────────────────────────
opts = Options()
opts.add_argument("--start-maximized")
opts.add_argument(f"--user-data-dir={USER_DATA}")
opts.add_argument(f"--profile-directory={PROFILE_NAME}")
opts.add_experimental_option("excludeSwitches", ["enable-automation"])
opts.add_experimental_option("useAutomationExtension", False)
driver = webdriver.Chrome(service=Service(CHROMEDRIVER), options=opts)

# ────────────────────────────────
# Helpers
# ────────────────────────────────
def ymd_iter(start: datetime, end: datetime):
    while start <= end:
        yield start
        start += timedelta(days=1)

def safe_find(selector: str, many=False, timeout=25):
    try:
        wait = WebDriverWait(driver, timeout)
        if many:
            return wait.until(lambda d: d.find_elements(By.CSS_SELECTOR, selector))
        return wait.until(lambda d: d.find_element(By.CSS_SELECTOR, selector))
    except TimeoutException:
        return [] if many else None

def build_prompt(date_obj: datetime, symbol: str = "BTC") -> str:
    ymd = date_obj.strftime("%Y-%m-%d")
    return "\n".join([
        "All output *must* be in English.",
        "Include *all* requested fields, only for the specified date.",
        "If a value is missing, fill it with the most recent available data.",
        "Remove any sources, links, or markdown.",
        "",
        f"Provide a **sentiment analysis report** for {ymd}.",
        "",
        "1. Sources to analyse",
        "   - Communities: r/cryptocurrency, r/bitcoin, r/ethtrader, r/CryptoMarkets",
        "   - Forums: Bitcointalk, CryptoCompare Forum, Steemit",
        "   - News: CoinDesk, Cointelegraph, The Block, Decrypt, Bloomberg Crypto, Reuters Crypto, CNBC Crypto",
        "",
        "2. Data volume",
        f"   - Community: all posts/comments or ≥100-item sample on {ymd}",
        f"   - News: all crypto/blockchain articles or ≥20-item sample on {ymd}",
        "",
        "3. Sentiment labels",
        "   - Optimistic (buy / bullish calls)",
        "   - Pessimistic (sell / critical)",
        "   - Neutral/Mixed",
        "",
        "4. Deliverables",
        "   1) Community sentiment distribution (%)",
        "   2) News tone distribution (%)",
        "   3) Key sentiment inflection points with 3-5 representative quotes",
        "   4) 3-5 hallmark quotes for each sentiment bucket",
        "",
        "---",
        f"{{DATE}} → {ymd}",
        f"{{SYMBOL}} → {symbol}",
    ])

def save_answer_to_snapshot(date_obj: datetime, answer_txt: str):
    if len(answer_txt.strip()) < 50:
        print(f"⚠️  Skipping save: answer too short for {date_obj.date()}")
        return

    date_str  = date_obj.strftime("%Y-%m-%d")
    json_path = (SNAPSHOT_ROOT / LOOP_NAME / EPISODE_NAME / date_str /
                 "market_snapshot.json")

    if not json_path.exists():
        print(f"⚠️  {json_path} not found – skipped")
        return

    try:
        with json_path.open(encoding="utf-8") as f:
            data = json.load(f)

        # Ensure nested structure
        rr = data.setdefault("research_reports", {})
        rr.setdefault("sentiment", []).append(answer_txt.strip())

        # Normalise timestamp (overwrite to be safe)
        data["timestamp_utc"] = (
            datetime.strptime(date_str, "%Y-%m-%d")
            .replace(tzinfo=timezone.utc)
            .isoformat()
            .replace("+00:00", "Z")
        )

        with json_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        rel = json_path.relative_to(SNAPSHOT_ROOT)
        print(f"📄  {rel} updated")
    except Exception as e:
        print(f"✖  JSON write error ({date_str}): {e}")

def open_new_chat():
    driver.get(CHATGPT_URL)
    if not safe_find('div.ProseMirror#prompt-textarea', timeout=60):
        raise RuntimeError("Input box not found – check login session")

def send_prompt_and_get_answer(date_obj: datetime):
    prompt_txt = build_prompt(date_obj)

    input_box = safe_find('div.ProseMirror#prompt-textarea', timeout=30)
    if not input_box:
        print("❌  입력창 찾기 실패"); return None

    input_box.click(); time.sleep(0.2)
    for line in prompt_txt.split("\n"):
        input_box.send_keys(line)
        input_box.send_keys(Keys.SHIFT, Keys.ENTER)
    input_box.send_keys(Keys.ENTER)
    print(f"⏳  {date_obj.date()} 프롬프트 전송")

    assist_sel = 'div[data-message-author-role="assistant"]'

    try:
        WebDriverWait(driver, 60).until(
            lambda d: len(d.find_elements(By.CSS_SELECTOR, assist_sel)) > 0
        )
    except TimeoutException:
        print("⚠️  응답 버블 생성 실패"); return None

    # 스트리밍 완료 감지
    last_txt, last_ts = "", time.time()
    while True:
        bubbles = driver.find_elements(By.CSS_SELECTOR, assist_sel)
        cur = "\n\n".join(b.text.strip() for b in bubbles)

        # 텍스트 변함 감지
        if cur != last_txt:
            last_txt, last_ts = cur, time.time()

        # STABLE_SEC 동안 변함 없으면 완료
        if time.time() - last_ts >= STABLE_SEC and len(cur) > 50:
            return cur

        # 최대 대기시간 초과 시 현재까지라도 반환
        if time.time() - last_ts >= RESP_MAX_SEC:
            print("⚠️  최대 대기 초과 — 부분 응답 반환")
            return cur

        time.sleep(1)

# ────────────────────────────────
# MAIN LOOP
# ────────────────────────────────
try:
    s_date = datetime.strptime(START_DATE, "%Y-%m-%d")
    e_date = datetime.strptime(END_DATE, "%Y-%m-%d")

    for day in ymd_iter(s_date, e_date):
        try:
            open_new_chat()
            answer = send_prompt_and_get_answer(day)
            if answer:
                save_answer_to_snapshot(day, answer)
            else:
                print(f"❌  {day.date()}: no response captured")
        except Exception as run_err:
            print(f"❌  Error on {day.date()}: {run_err}")
            traceback.print_exc()

        if day < e_date:
            time.sleep(DAY_PAUSE + POST_WAIT)

except KeyboardInterrupt:
    print("\n🛑  Aborted by user")
except Exception as fatal:
    print("❌  Fatal error:", fatal)
    traceback.print_exc()
finally:
    driver.quit()
    print("🚪  Browser session closed")
