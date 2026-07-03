# GitHub Actions로 5분마다 MSTU 알림 받기

이 방식은 PC를 꺼도 GitHub 서버가 5분마다 확인해서 텔레그램으로 알림을 보냅니다.

## 1. GitHub 저장소 만들기

GitHub에서 새 저장소를 만드세요.

추천:

- Repository name: `mstu-telegram-alert`
- Visibility: `Private`

Private로 만드는 걸 추천합니다.

## 2. 파일 올리기

이 폴더 안의 파일들을 GitHub 저장소에 올립니다.

중요:

- `settings.txt`는 올리지 마세요.
- `.env`도 올리지 마세요.
- `.gitignore`가 있어서 보통은 자동으로 제외됩니다.

GitHub 저장소 첫 화면 기준으로 아래 파일들이 보여야 합니다.

```text
mstu_alert.py
README.md
GITHUB_ACTIONS_SETUP.md
.github/workflows/mstu-alert.yml
```

## 3. GitHub Secrets 넣기

저장소에서 아래로 이동하세요.

```text
Settings -> Secrets and variables -> Actions -> New repository secret
```

아래 2개를 각각 추가합니다.

```text
TELEGRAM_BOT_TOKEN
```

값에는 BotFather가 준 봇 토큰을 넣습니다.

```text
TELEGRAM_CHAT_ID
```

값에는 텔레그램 chat_id를 넣습니다.

## 4. Actions 켜기

저장소 상단의 `Actions` 탭으로 갑니다.

처음이면 GitHub가 workflow 사용을 확인할 수 있습니다. 안내가 나오면 허용하세요.

## 5. 수동 테스트

`Actions` 탭에서 `MSTU Telegram Alert`를 선택합니다.

그 다음:

```text
Run workflow
```

를 눌러 한 번 실행하세요.

성공하면 이후부터 5분마다 자동 확인합니다.

## 6. 알림 주기

현재 설정은 아래와 같습니다.

```yaml
cron: "2-59/5 * * * *"
```

즉 매시 2분, 7분, 12분, 17분처럼 약 5분마다 실행합니다.

GitHub 공식 문서 기준으로 예약 workflow의 가장 짧은 간격은 5분입니다. 또 GitHub 사용량이 많은 시간에는 예약 실행이 지연되거나 드물게 누락될 수 있습니다.

## 7. 중복 알림 방지

실행 후 `state.json` 파일이 저장소에 생깁니다.

이 파일은 이미 본 소식을 기억하는 기록입니다. 지우면 과거 소식이 다시 알림으로 올 수 있습니다.

