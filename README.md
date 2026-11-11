# AI 비서 🤖

정해진 날 아침 8시에 일정을 카카오톡 "나와의 채팅"으로 알려줍니다.

## 흐름
1. ⏰ GitHub Actions가 아침에 30분마다 `main.py` 실행
2. 📅 `schedules.json`에서 오늘 알릴 일정 찾기
3. 🧠 Gemini가 준비물·팁 3줄 덧붙이기 (날짜는 코드가 직접 적음 → AI가 숫자 틀릴 일 없음)
4. 📱 카카오톡으로 보내기, `sent_log.json`에 기록 (하루 한 번만)

## 일정 추가하기
`schedules.json`의 `schedules` 목록에 한 덩어리 추가 → GitHub에 올리기.

```json
{ "title": "기말고사", "date": "2026-12-15", "remind_days_before": [7, 1, 0], "note": "" }
```

## 금고(Secrets)에 들어 있는 것
`KAKAO_REST_API_KEY`, `KAKAO_CLIENT_SECRET`, `KAKAO_REFRESH_TOKEN`, `GEMINI_API_KEY`

## 테스트
GitHub → Actions → "AI 비서 알림" → Run workflow (Gemini 무료 한도가 있으니 1~2번만)
