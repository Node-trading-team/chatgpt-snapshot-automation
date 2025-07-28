\# 🚀 ChatGPT Snapshot Automation



Python + Selenium 스크립트를 이용해 ChatGPT로부터 날짜별 \*fundamental\* 리포트를 받아  

`daily\_snapshots/.../market\_snapshot.json` 파일에 즉시 저장하는 자동화 도구입니다.



---



\## 📦 전제 조건

\- \*\*운영체제\*\*: Windows 10/11  

\- \*\*Python\*\*: 3.8 이상  

\- \*\*Git\*\*: 설치 및 기본 설정 완료  

\- \*\*Chrome\*\*: 최신 버전 (ChromeDriver 버전과 일치 필수)  



---



\## 🛠️ 설치 및 환경 설정



1\. \*\*리포지토리 클론\*\*

&nbsp;  ```powershell

&nbsp;  cd "C:\\Users\\dkdlt\\db\\db\_train\\Trend Analyst"

&nbsp;  git clone https://github.com/Node-trading-team/chatgpt-snapshot-automation.git

&nbsp;  cd chatgpt-snapshot-automation



2\. ChromeDriver 설치

&nbsp;   Chrome → ⋮ → 도움말 → Chrome 정보 에서 버전 확인

&nbsp;   https://chromedriver.chromium.org/downloads 에서 동일 버전 ZIP 다운로드

&nbsp;   압축 해제 후, chromedriver.exe를

&nbsp;   프로젝트 drivers/ 폴더에 복사

&nbsp;   또는 시스템 PATH 경로에 복사



3\. Python 패키지 설치 

&nbsp;   pip install selenium



4\. Chrome 사용자 프로필 로그인

&nbsp;   start "" chrome.exe --user-data-dir="%CD%\\chrome-data\\user-profile" --profile-directory="Default"

이 창에서 ChatGPT(https://chat.openai.com) 로그인

로그인 완료 후 \*\*창을 꼭 닫아야함\*\* 

이후 스크립트가 동일 user-data-dir 사용해 자동 로그인



5.from pathlib import Path



chrome\_driver\_path = r"drivers\\chromedriver.exe"

user\_data\_dir      = r"chrome-data\\user-profile"

profile\_name       = "Default"

chatgpt\_url        = "https://chat.openai.com"



start\_date         = "2018-01-01"

end\_date           = "2018-01-02"

delay\_between\_days = 15



SNAPSHOT\_ROOT      = Path(r"C:\\Users\\dkdlt\\db\\db\_train\\Trend Analyst\\daily\_snapshots")

LOOP\_NAME          = "loop1"

EPISODE\_NAME       = "episode13"  --> 스크래핑 하고자 하는 파일 경로에 맞게 수정



STABLE\_SEC         = 60    # 응답 안정화(초)

POST\_WAIT          = 15    # 저장 후 대기(초)

RESP\_MAX\_SEC       = 420   # 최대 응답 대기(초)



⚠️ 주의사항

ChromeDriver 버전 ↔ Chrome 버전 일치 필수



chrome-data\\user-profile 폴더 삭제/이동 시 재로그인 필요

\*\*\* GPT 로봇 감지 방지 ( 무한 반복 뜬다면 ) 다시 4번 코드 한줄 cmd 창에서 실행시키고 gpt 들어가서 로봇이 아닙니다 체크 후 크롬 닫고 다시 코드 실행

너무 짧은 반복 실행 금지

delay\_between\_days, POST\_WAIT 를 30초 이상 권장

타임아웃 조정

STABLE\_SEC, RESP\_MAX\_SEC, safe\_find 타임아웃(기본 25초) 조절 가능

