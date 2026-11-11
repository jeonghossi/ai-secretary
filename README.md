# AI 비서 🤖

정해진 날 아침 8시에 일정을 카카오톡 "나와의 채팅"으로 알려줍니다.

## 흐름
1. ⏰ GitHub Actions가 아침에 30분마다 `main.py` 실행
2. 📅 `schedules.json`에서 오늘 알릴 일정 찾기
3. 🧠 Gemini가 준비물·팁 3줄 덧붙이기 (날짜는 코드가 직접 적음 → AI가 숫자 틀릴 일 없음)
4. 📱 카카오톡으로 보내기, `sent_log.json`에 기록 (하루 한 번만)

## 일정 추가하기 ⭐ 구글 캘린더
구글 캘린더(폰 앱 OK)에 일정을 넣기만 하면 됩니다. 매일 아침 자동으로 읽어요.
- 기본: 일주일 전·하루 전·당일 알림 (매주 반복 일정은 당일만)
- 바꾸고 싶으면 일정 **설명**에 `알림: 3,0` 처럼 적기 (3일 전과 당일)
- 장소·시간도 알림에 같이 나옴
- 금고의 `GCAL_ICS_URL` = 구글 캘린더 설정 → 내 캘린더 → 캘린더 통합 → "iCal 형식의 비공개 주소"

## 일정 추가하기 (예비) schedules.json
`schedules.json`의 `schedules` 목록에 한 덩어리 추가 → GitHub에 올리기.

```json
{ "title": "기말고사", "date": "2026-12-15", "remind_days_before": [7, 1, 0], "note": "" }
```

## 금고(Secrets)에 들어 있는 것
`KAKAO_REST_API_KEY`, `KAKAO_CLIENT_SECRET`, `KAKAO_REFRESH_TOKEN`, `GEMINI_API_KEY`

## 테스트
GitHub → Actions → "AI 비서 알림" → Run workflow (Gemini 무료 한도가 있으니 1~2번만)
