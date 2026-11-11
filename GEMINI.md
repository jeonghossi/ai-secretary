# AI 비서 프로젝트 안내 (AI 도우미용)

이 폴더는 일정이 다가오면 카카오톡으로 알려주는 프로그램이다.
사용자가 일정 추가·수정·삭제를 부탁하면 **schedules.json 만 고친다.**

## 일정 형식
`schedules.json` 의 `"schedules"` 목록에 아래 형태로 한 덩어리씩 넣는다.

```json
{
  "title": "기말고사",
  "date": "2026-12-15",
  "remind_days_before": [7, 1, 0],
  "note": "오전 10시 / 공학관 301호"
}
```

- `title`: 일정 이름
- `date`: 반드시 `YYYY-MM-DD` (예: 2026-12-15). 연도를 안 말하면 다가오는 날짜 기준으로 정한다
- `remind_days_before`: 며칠 전에 알릴지 숫자 목록. 0 = 당일, 1 = 하루 전, 7 = 일주일 전. 말이 없으면 `[7, 1, 0]`
- `note`: 시간·장소 등 메모. 없으면 `""`
- 알림은 해당 날 오전 8시쯤 온다

## 꼭 지킬 것
- 덩어리 사이에 쉼표(,)를 빠뜨리지 말고, JSON 문법이 맞는지 확인한다 (틀리면 알림이 전부 멈춤)
- 기존 일정은 사용자가 지우라고 하지 않으면 그대로 둔다
- `main.py`, `.github/workflows/notify.yml`, `sent_log.json` 은 고치지 않는다
- API 키·토큰을 파일에 절대 적지 않는다 (GitHub Secrets 에 있음)

## 고친 뒤
GitHub 에 올려야 반영된다:
```
git add schedules.json
git commit -m "일정 추가: <일정 이름>"
git push
```
