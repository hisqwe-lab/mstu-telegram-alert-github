# MSTU Telegram Alert

MSTU 분할, 병합, 역분할 관련 소식을 감시해서 텔레그램으로 보내는 작은 알림 프로그램입니다.

## 1. 준비물

- Telegram 봇 토큰
- Telegram chat_id
- Python 3

## 2. 설정 파일 입력하기

이 폴더에 `settings.txt` 파일을 만들어두었습니다. 그 안에 값을 넣습니다.

```text
TELEGRAM_BOT_TOKEN=봇토큰
TELEGRAM_CHAT_ID=chat_id
ALERT_ON_FIRST_RUN=0
```

`ALERT_ON_FIRST_RUN=0`은 첫 실행 때 이미 보이는 과거 글은 조용히 저장하고, 다음부터 새로 잡힌 것만 알림을 보냅니다.

`.env`와 `.env.example`은 예비 복사본입니다.

## 3. 테스트 알림 보내기

PowerShell에서 이 폴더로 이동한 뒤 실행하세요.

```powershell
.\run_test.ps1
```

텔레그램에 테스트 메시지가 오면 준비 완료입니다.

## 4. 한 번만 감시 실행하기

```powershell
.\run_once.ps1
```

## 5. 감시 사이트와 키워드 보기

텔레그램을 보내지 않고, 어떤 사이트와 키워드를 감시하는지만 봅니다.

```powershell
.\show_sources.ps1
```

실제로 각 사이트를 확인하고, 현재 잡히는 항목을 화면에 미리 봅니다.

```powershell
.\preview_sources.ps1
```

## 6. 5분마다 자동 실행 등록하기

PowerShell을 열고 이 폴더에서 실행하세요.

```powershell
.\setup_windows_task.ps1
```

기본값은 5분마다 실행입니다. 더 빠르게 원하면 아래처럼 1분으로 등록할 수 있습니다.

```powershell
.\setup_windows_task.ps1 -Minutes 1
```

## 7. 자동 실행 해제하기

```powershell
.\remove_windows_task.ps1
```

## PC를 꺼도 받기

PC를 꺼도 알림을 받고 싶다면 GitHub Actions 버전을 사용하세요.

[GitHub Actions 설정 방법](GITHUB_ACTIONS_SETUP.md)

## 감시하는 곳

- REX Shares MSTU 공식 페이지
- REX Shares News & Insights
- SEC EDGAR MSTU 검색 피드
- Google News MSTU split/reverse split 검색 RSS

무료 웹 감시라 100% 즉시성은 보장할 수 없습니다. 그래도 1-5분 간격이면 개인용으로는 꽤 빠르게 잡을 수 있습니다.

## Python 관련 참고

이 폴더의 PowerShell 파일들은 아래 순서로 Python을 찾습니다.

1. `python`
2. `py`
3. Codex에 포함된 Python

그래서 보통은 Python 경로를 직접 찾지 않아도 됩니다.
