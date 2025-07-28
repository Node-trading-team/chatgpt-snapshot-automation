"""
ChatGPT Selenium 수집 → market_snapshot.json 즉시 업데이트
rev. 2025-07-21 (only-file version, timing optimized)

필요 패키지: selenium  (pip install selenium)
"""
# ──────────────────────────────────────────────────────────────
from pathlib import Path
from datetime import datetime, timedelta, timezone
import time, json, traceback

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import (
    NoSuchElementException, StaleElementReferenceException, TimeoutException,
)
# ──────────────────────────────────────────────────────────────

# ────────── 사용자 설정 ──────────
chrome_driver_path = r"C:\chrome-data\chromedriver.exe"
user_data_dir      = r"C:\chrome-data\user-profile"
profile_name       = "Default"
chatgpt_url        = "https://chat.openai.com"

start_date         = "2018-01-01"
end_date           = "2018-01-02"
delay_between_days = 15  # 날짜 간 간격(초)

SNAPSHOT_ROOT = Path(r"C:\Users\dkdlt\db\db_train\Trend Analyst\daily_snapshots")
LOOP_NAME     = "loop1"
EPISODE_NAME  = "episode13"

# ───── 타이밍 파라미터 ─────
STABLE_SEC   = 60   # 텍스트가 STABLE_SEC초 동안 안 바뀌면 완료로 판단
POST_WAIT    = 15   # 저장 후 추가 대기
RESP_MAX_SEC = 420  # 답변 최대 대기(안정 판정 포함)

# ───── Selenium 옵션 ─────
opts = Options()
opts.add_argument("--start-maximized")
opts.add_argument(f"--user-data-dir={user_data_dir}")
opts.add_argument(f"--profile-directory={profile_name}")
opts.add_experimental_option("excludeSwitches", ["enable-automation"])
opts.add_experimental_option("useAutomationExtension", False)
driver = webdriver.Chrome(service=Service(chrome_driver_path), options=opts)

# ───── 헬퍼 ─────
def ymd_iter(s: datetime, e: datetime):
    while s <= e:
        yield s
        s += timedelta(days=1)

def safe_find(selector, many=False, timeout=25):
    try:
        w = WebDriverWait(driver, timeout)
        return (
            w.until(lambda d: d.find_elements(By.CSS_SELECTOR, selector))
            if many else
            w.until(lambda d: d.find_element(By.CSS_SELECTOR, selector))
        )
    except TimeoutException:
        return [] if many else None

# Stale-safe collector
def collect_assistant_text(selector: str) -> str:
    last_txt, last_ts = "", time.time()
    while True:
        try:
            bubbles = driver.find_elements(By.CSS_SELECTOR, selector)
            cur = "\n\n".join(b.text.strip() for b in bubbles)
        except StaleElementReferenceException:
            time.sleep(0.3)
            continue  # 다시 시도

        if cur != last_txt:
            last_txt, last_ts = cur, time.time()

        if time.time() - last_ts >= STABLE_SEC and len(cur) > 50:
            return cur

        if time.time() - last_ts >= RESP_MAX_SEC:
            print("⚠️  최대 대기 초과 — 부분 응답 반환")
            return cur

        time.sleep(1)

# ───── 프롬프트 빌더 ─────
def build_prompt(date_obj: datetime, symbol: str = "BTC") -> str:
    ymd = date_obj.strftime("%Y-%m-%d")
    return "\n".join([
        "All output *must* be in English.",
        "All fields *must* be included, and *strictly* for the specified date only.",
        "If any value is missing, fill it with the *most recent* available data prior to that date.",
        "The result *must* exclude all sources, links, markers, or markdown formatting.",
        "Do *not* include any references or citations in the output.",
        "The report *must* include all items listed below.",
        "",
        f"Generate a fundamental information report for {ymd}, including the following contents.",
        "",
        "Items to exclude:",
        "- Charts or technical indicators (e.g., RSI, MACD)",
        "- Sentiment analysis or subjective opinions",
        "",
        "---",
        "",
        f"[Date: {ymd}, Asset: {symbol}]",
        "",
        "1. Quantitative Market Indicators",
        "- 24h trading volume",
        "- 7-day average trading volume",
        "- 7-day realized volatility",
        "- Implied volatility",
        "- Funding rate",
        "- Open interest",
        "",
        "2. On-chain Indicators",
        "- Hash rate",
        "- Staking participation rate",
        "- Total network fees",
        "- Average transaction fee",
        "- NVT ratio",
        "",
        "3. Macroeconomic Indicators",
        "- U.S. Federal Funds Rate",
        "- U.S. Dollar Index (DXY):",
        "  • 1-week change",
        "  • 1-month change",
        "- M2 Money Supply",
        "- 30-day correlation with S&P 500",
        "- 30-day correlation with Nasdaq",
        "",
        "4. Interpretations",
        "- Summary of market conditions",
        "- Summary of on-chain analysis",
        "- Summary of macroeconomic context",
        "",
        "5. Final Summary",
        "- Key fundamental strengths",
        "- Major risks",
        "- Overall outlook",
        "",
        "---",
        f"{{DATE}} → {ymd}",
        f"{{SYMBOL}} → {symbol}",
    ])

# ───── JSON 저장 ─────
def save_answer_to_snapshot(date_obj: datetime, answer_txt: str):
    date_str  = date_obj.strftime("%Y-%m-%d")
    json_path = SNAPSHOT_ROOT / LOOP_NAME / EPISODE_NAME / date_str / "market_snapshot.json"

    if not json_path.exists():
        print(f"⚠️  {json_path} 없음 → 건너뜀")
        return

    try:
        with json_path.open(encoding="utf-8") as f:
            data = json.load(f)

        # fundamental 누적 저장
        reports = data.setdefault("research_reports", {})
        reports.setdefault("fundamental", []).append(answer_txt.strip())

        # timestamp 갱신
        data["timestamp_utc"] = (
            datetime.strptime(date_str, "%Y-%m-%d")
                    .replace(tzinfo=timezone.utc)
                    .isoformat()
                    .replace("+00:00", "Z")
        )

        with json_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        rel = json_path.relative_to(SNAPSHOT_ROOT)
        print(f"📄  {rel} 업데이트 완료")
    except Exception as e:
        print(f"✖️  JSON 저장 오류 ({date_str}): {e}")

# ───── ChatGPT 새 대화 열기 ─────
def open_new_chat():
    driver.get(chatgpt_url)
    if not safe_find('div.ProseMirror#prompt-textarea', timeout=60):
        raise RuntimeError("입력창 로드 실패 — 로그인 세션 확인")

# ───── 프롬프트 전송 & 응답 수집 ─────
def send_prompt_and_get_answer(date_obj: datetime):
    prompt_txt = build_prompt(date_obj)

    input_box = safe_find('div.ProseMirror#prompt-textarea', timeout=30)
    if not input_box:
        print("❌  입력창 찾기 실패"); return None

    input_box.click(); time.sleep(0.2)
    # 한 줄씩 SHIFT+ENTER 입력
    for line in prompt_txt.split("\n"):
        input_box.send_keys(line)
        input_box.send_keys(Keys.SHIFT, Keys.ENTER)
    # 최종 전송
    input_box.send_keys(Keys.ENTER)
    print(f"⏳  {date_obj.date()} 프롬프트 전송")

    assist_sel = 'div[data-message-author-role="assistant"]'
    # 말풍선 생성 대기
    try:
        WebDriverWait(driver, STABLE_SEC).until(
            lambda d: len(d.find_elements(By.CSS_SELECTOR, assist_sel)) > 0
        )
    except TimeoutException:
        print("⚠️  응답 버블 생성 실패"); return None

    # 스트리밍 완료까지 수집
    return collect_assistant_text(assist_sel)

# ───── 메인 실행 ─────
try:
    s_date = datetime.strptime(start_date, "%Y-%m-%d")
    e_date = datetime.strptime(end_date,   "%Y-%m-%d")

    for d in ymd_iter(s_date, e_date):
        try:
            open_new_chat()
            answer_txt = send_prompt_and_get_answer(d)
            if answer_txt:
                save_answer_to_snapshot(d, answer_txt)
            else:
                print(f"❌  {d.date()} : 응답 확보 실패")
        except Exception as inner:
            print(f"❌  {d.date()} 처리 중 오류:", inner)
            traceback.print_exc()

        # 날짜 간 대기 + POST_WAIT
        if d < e_date:
            time.sleep(delay_between_days + POST_WAIT)

except KeyboardInterrupt:
    print("\n🛑  사용자 중단")
except Exception as e:
    print("❌  치명적 오류:", e)
    traceback.print_exc()
finally:
    driver.quit()
    print("🚪  브라우저 세션 종료")
