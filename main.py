"""AI 비서: 일정이 다가오면 카카오톡 '나와의 채팅'으로 알려준다.

GitHub Actions가 아침에 30분마다 이 파일을 실행한다.
- 한국 시간 SEND_HOUR 전이면 그냥 끝낸다.
- 오늘 이미 보냈으면 그냥 끝낸다 (sent_log.json 에 기록).
- 알릴 일정이 있으면 Gemini가 준비물·팁을 덧붙이고 카톡으로 보낸다.
"""
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path

import requests

SEND_HOUR = 8  # 한국 시간 오전 8시부터 보냄
KST = dt.timezone(dt.timedelta(hours=9))
HERE = Path(__file__).parent
LOG_FILE = HERE / "sent_log.json"
WEEKDAYS = "월화수목금토일"

KAKAO_REST_API_KEY = os.environ.get("KAKAO_REST_API_KEY", "")
KAKAO_CLIENT_SECRET = os.environ.get("KAKAO_CLIENT_SECRET", "")
KAKAO_REFRESH_TOKEN = os.environ.get("KAKAO_REFRESH_TOKEN", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GCAL_ICS_URL = os.environ.get("GCAL_ICS_URL", "")  # 구글 캘린더 '비공개 주소(iCal 형식)'
DEFAULT_REMIND = [7, 1, 0]  # 캘린더 일정은 일주일 전·하루 전·당일에 알림
FORCE = os.environ.get("FORCE", "").lower() == "true"  # 테스트: 시간·중복 검사 없이 바로 보내기


# ---------- 카카오톡 ----------
def get_kakao_access_token():
    """재발급권(refresh token)으로 오늘 쓸 출입증(access token)을 받는다."""
    r = requests.post(
        "https://kauth.kakao.com/oauth/token",
        data={
            "grant_type": "refresh_token",
            "client_id": KAKAO_REST_API_KEY,
            "client_secret": KAKAO_CLIENT_SECRET,
            "refresh_token": KAKAO_REFRESH_TOKEN,
        },
        timeout=20,
    )
    data = r.json()
    if "access_token" not in data:
        sys.exit(f"카카오 토큰 발급 실패: {data}")
    # 재발급권 만료가 한 달 안쪽이면 카카오가 새 재발급권을 준다 → 나에게 알려서 금고에 갈아 끼우게 함
    new_refresh = data.get("refresh_token")
    return data["access_token"], new_refresh


def send_kakao(access_token, text):
    """카톡 텍스트 메시지는 200자 제한이 있어서 길면 나눠 보낸다."""
    for chunk in split_text(text, 200):
        r = requests.post(
            "https://kapi.kakao.com/v2/api/talk/memo/default/send",
            headers={"Authorization": f"Bearer {access_token}"},
            data={
                "template_object": json.dumps(
                    {
                        "object_type": "text",
                        "text": chunk,
                        "link": {"web_url": "https://calendar.google.com", "mobile_web_url": "https://calendar.google.com"},
                    },
                    ensure_ascii=False,
                )
            },
            timeout=20,
        )
        result = r.json()
        if result.get("result_code") != 0:
            sys.exit(f"카톡 보내기 실패: {result}")


def split_text(text, limit):
    chunks, cur = [], ""
    for line in text.split("\n"):
        while len(line) > limit:  # 한 줄이 너무 길면 강제로 자름
            if cur:
                chunks.append(cur)
                cur = ""
            chunks.append(line[:limit])
            line = line[limit:]
        candidate = f"{cur}\n{line}" if cur else line
        if len(candidate) > limit:
            chunks.append(cur)
            cur = line
        else:
            cur = candidate
    if cur:
        chunks.append(cur)
    return chunks


# ---------- Gemini ----------
def ask_gemini_tips(title, note):
    """준비물·팁 3가지. 실패하면 빈 문자열 (알림은 그래도 감)."""
    if not GEMINI_API_KEY:
        return ""
    prompt = (
        f"일정: {title}\n"
        f"메모: {note or '없음'}\n\n"
        "이 일정을 앞둔 사람에게 챙길 준비물이나 팁을 한국어로 딱 3줄만 써줘.\n"
        "규칙: 각 줄은 '• '로 시작, 한 줄 40자 이내, 전체 130자 이내.\n"
        "날짜·시간·장소·금액·전화번호처럼 확실하지 않은 숫자나 사실은 절대 지어내지 마. "
        "기관마다 다를 수 있는 건 '안내문 확인' 처럼 일반적으로 말해."
    )
    for model in ("gemini-flash-latest", "gemini-2.5-flash"):
        try:
            r = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                headers={"x-goog-api-key": GEMINI_API_KEY, "Content-Type": "application/json"},
                json={"contents": [{"parts": [{"text": prompt}]}]},
                timeout=60,
            )
            data = r.json()
            text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
            return text
        except Exception as e:  # 모델 이름 바뀜·한도 초과 등
            print(f"Gemini({model}) 실패: {e} / {str(locals().get('data'))[:300]}")
    return ""


# ---------- 일정 ----------
def d_label(days):
    return "오늘" if days == 0 else ("내일" if days == 1 else f"D-{days}")


def build_message(item, days):
    date = dt.date.fromisoformat(item["date"])
    # 날짜는 AI가 아니라 코드가 직접 적는다 (AI가 숫자를 틀리는 것 방지)
    lines = [
        f"📅 [{d_label(days)}] {item['title']}",
        f"날짜: {date.month}월 {date.day}일 ({WEEKDAYS[date.weekday()]})",
    ]
    if item.get("note"):
        lines.append(f"메모: {item['note']}")
    tips = ask_gemini_tips(item["title"], item.get("note", ""))
    if tips:
        lines += ["", "🤖 AI 비서 준비 팁", tips]
    return "\n".join(lines)


def fmt_time(t):
    ampm = "오전" if t.hour < 12 else "오후"
    h12 = t.hour % 12 or 12
    mm = f" {t.minute}분" if t.minute else ""
    return f"{ampm} {h12}시{mm}({t:%H:%M})"


def parse_remind(desc, recurring=False):
    """설명에 '알림: 3,1,0' 이라고 적으면 그 날짜에 알림. 없으면 기본값 (반복 일정은 당일만)."""
    m = re.search(r"알림\s*[:：]\s*([\d,\s]+)", desc or "")
    if m:
        days = [int(x) for x in re.findall(r"\d+", m.group(1))]
        if days:
            return days
    return [0] if recurring else DEFAULT_REMIND


def load_calendar_events(today):
    """구글 캘린더에서 오늘~앞으로 31일 일정을 가져와 schedules.json 과 같은 모양으로 바꾼다."""
    if not GCAL_ICS_URL:
        return []
    import icalendar
    import recurring_ical_events

    try:
        r = requests.get(GCAL_ICS_URL, timeout=30)
        r.raise_for_status()
        cal = icalendar.Calendar.from_ical(r.content)
    except Exception as e:
        print(f"구글 캘린더 읽기 실패: {e}")
        return []

    start = dt.datetime.combine(today, dt.time(0), KST)
    recurring_uids = {str(c.get("UID")) for c in cal.walk("VEVENT") if "RRULE" in c}
    events = []
    for ev in recurring_ical_events.of(cal).between(start, start + dt.timedelta(days=32)):
        title = str(ev.get("SUMMARY", "(제목 없음)")).strip()
        s = ev.get("DTSTART").dt
        parts = []
        if isinstance(s, dt.datetime):
            s = s.astimezone(KST) if s.tzinfo else s.replace(tzinfo=KST)
            date = s.date()
            parts.append(fmt_time(s))
        else:  # 하루 종일 일정
            date = s
        loc = str(ev.get("LOCATION", "")).strip()
        if loc:
            parts.append(loc)
        desc = str(ev.get("DESCRIPTION", "")).strip()
        first_line = re.sub(r"<[^>]+>", " ", desc).split("\n")[0].strip()
        if first_line and not first_line.startswith("알림"):
            parts.append(first_line[:60])
        events.append(
            {
                "title": title,
                "date": date.isoformat(),
                "remind_days_before": parse_remind(desc, str(ev.get("UID")) in recurring_uids),
                "note": " / ".join(parts),
            }
        )
    print(f"구글 캘린더에서 일정 {len(events)}개 읽음")
    return events


def load_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default


def main():
    now = dt.datetime.now(KST)
    today = now.date()
    log = load_json(LOG_FILE, {"sent_dates": []})
    print(f"지금 한국 시간: {now:%Y-%m-%d %H:%M}, 테스트 모드: {FORCE}")

    if not FORCE:
        if now.hour < SEND_HOUR:
            print(f"아직 {SEND_HOUR}시 전이라 쉬어요.")
            return
        if today.isoformat() in log["sent_dates"]:
            print("오늘은 이미 보냈어요.")
            return

    schedules = load_json(HERE / "schedules.json", {"schedules": []})["schedules"]
    seen = {(s["title"], s["date"]) for s in schedules}
    for ev in load_calendar_events(today):  # 같은 제목·날짜는 한 번만
        if (ev["title"], ev["date"]) not in seen:
            schedules.append(ev)
            seen.add((ev["title"], ev["date"]))
    due = []
    for item in schedules:
        days = (dt.date.fromisoformat(item["date"]) - today).days
        if days in item.get("remind_days_before", [0]):
            due.append((item, days))

    if not due and not FORCE:
        print("오늘 알릴 일정이 없어요.")
        return

    access_token, new_refresh = get_kakao_access_token()

    if due:
        for item, days in due:
            send_kakao(access_token, build_message(item, days))
            print(f"보냄: {item['title']} ({d_label(days)})")
    else:  # 테스트인데 오늘 알릴 일정이 없을 때 → 다가오는 일정 목록
        upcoming = sorted(
            (s for s in schedules if dt.date.fromisoformat(s["date"]) >= today), key=lambda s: s["date"]
        )
        text = "🧪 AI 비서 테스트 메시지\n오늘 알릴 일정은 없어요.\n\n다가오는 일정:"
        for s in upcoming[:5]:
            d = dt.date.fromisoformat(s["date"])
            text += f"\n• {d.month}/{d.day} {s['title']} (D-{(d - today).days})"
        send_kakao(access_token, text)
        print("테스트 메시지 보냄")

    if new_refresh:
        send_kakao(
            access_token,
            "🔑 카카오 재발급권이 새로 나왔어요.\nGitHub → Settings → Secrets 의 KAKAO_REFRESH_TOKEN 을 아래 값으로 바꿔주세요.\n"
            + new_refresh,
        )

    if not FORCE and due:
        log["sent_dates"] = (log["sent_dates"] + [today.isoformat()])[-60:]
        LOG_FILE.write_text(json.dumps(log, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
