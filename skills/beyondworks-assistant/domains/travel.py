"""Travel domain handler — 여행 관리"""
import json
from datetime import datetime, timedelta
from core.config import get_domain_config
from core.notion_client import query_database, create_page, update_page, parse_page_properties
from core.openai_client import chat_with_tools, chat_completion
from core.history import add_to_history, get_recent_history

DOMAIN = "travel"

def _cfg():
    return get_domain_config(DOMAIN)

def _db(key):
    return _cfg().get("databases", {}).get(key, "")

SYSTEM_PROMPT = """당신은 여행 관리 비서입니다. 여행 계획, 일정, 예약, 준비물을 관리합니다.

## 역할
- 여행 목록 및 D-day 조회
- 세부 일정 조회/추가
- 예약 현황 확인
- 준비물 체크리스트 관리

## 응답 스타일
- 한국어, 간결하게, 이모지 활용"""

TOOLS = [
    {"type": "function", "function": {
        "name": "get_trips",
        "description": "여행 목록 및 D-day 조회",
        "parameters": {"type": "object", "properties": {
            "status": {"type": "string", "description": "upcoming, ongoing, past 중 택1"}
        }}
    }},
    {"type": "function", "function": {
        "name": "get_trip_detail",
        "description": "특정 여행의 세부 일정 조회",
        "parameters": {"type": "object", "properties": {
            "trip_name": {"type": "string", "description": "여행 이름 (키워드 검색)"}
        }, "required": ["trip_name"]}
    }},
    {"type": "function", "function": {
        "name": "get_reservations",
        "description": "예약 현황 조회",
        "parameters": {"type": "object", "properties": {
            "trip_name": {"type": "string", "description": "여행 이름 (선택)"}
        }}
    }},
    {"type": "function", "function": {
        "name": "get_packing_list",
        "description": "준비물 체크리스트 조회",
        "parameters": {"type": "object", "properties": {
            "trip_name": {"type": "string", "description": "여행 이름 (선택)"}
        }}
    }},
    {"type": "function", "function": {
        "name": "check_packing_item",
        "description": "준비물 체크/해제",
        "parameters": {"type": "object", "properties": {
            "item_name": {"type": "string", "description": "준비물 항목명"},
            "checked": {"type": "boolean", "description": "체크 여부"}
        }, "required": ["item_name"]}
    }}
]

def _query_trips(status=None):
    today = datetime.now().strftime('%Y-%m-%d')
    filt = None
    if status == "upcoming":
        filt = {"property": "Date", "date": {"after": today}}
    elif status == "past":
        filt = {"property": "Date", "date": {"before": today}}
    r = query_database(_db("trips"),
                       filter_obj=filt,
                       sorts=[{"property": "Date", "direction": "ascending"}],
                       page_size=20)
    if isinstance(r, dict) and r.get("success"):
        return [parse_page_properties(p) for p in r.get("results", [])]
    return []

def _query_itinerary(keyword=None):
    filt = None
    if keyword:
        filt = {"property": "Name", "title": {"contains": keyword}}
    r = query_database(_db("itinerary"),
                       filter_obj=filt,
                       sorts=[{"property": "Date", "direction": "ascending"}],
                       page_size=30)
    if isinstance(r, dict) and r.get("success"):
        return [parse_page_properties(p) for p in r.get("results", [])]
    return []

def _query_reservations(keyword=None):
    filt = None
    if keyword:
        filt = {"property": "Name", "title": {"contains": keyword}}
    r = query_database(_db("reservations"),
                       filter_obj=filt,
                       sorts=[{"property": "Date", "direction": "ascending"}],
                       page_size=20)
    if isinstance(r, dict) and r.get("success"):
        return [parse_page_properties(p) for p in r.get("results", [])]
    return []

def _query_packing(keyword=None):
    filt = None
    if keyword:
        filt = {"property": "Name", "title": {"contains": keyword}}
    r = query_database(_db("packing"),
                       filter_obj=filt,
                       page_size=50)
    if isinstance(r, dict) and r.get("success"):
        return [parse_page_properties(p) for p in r.get("results", [])]
    return []

def _calc_dday(date_str):
    if not date_str:
        return ""
    try:
        target = datetime.strptime(date_str[:10], '%Y-%m-%d')
        diff = (target - datetime.now()).days
        if diff > 0:
            return f"D-{diff}"
        elif diff == 0:
            return "D-Day!"
        else:
            return f"D+{abs(diff)}"
    except Exception:
        return ""

def _exec_tool(name, args):
    if name == "get_trips":
        status = args.get("status")
        trips = _query_trips(status)
        if trips:
            lines = ["✈️ 여행 목록:"]
            for t in trips:
                trip_name = t.get("Name", t.get("이름", ""))
                date = t.get("Date", {})
                start = date.get("start", "") if isinstance(date, dict) else ""
                end = date.get("end", "") if isinstance(date, dict) else ""
                dday = _calc_dday(start)
                date_str = f"{start}" + (f" ~ {end}" if end else "")
                lines.append(f"- {trip_name} ({date_str}) {dday}")
            return "\n".join(lines)
        return "여행 정보가 없습니다."

    if name == "get_trip_detail":
        keyword = args.get("trip_name", "")
        items = _query_itinerary(keyword)
        if items:
            lines = [f"📋 '{keyword}' 세부 일정 ({len(items)}건):"]
            for it in items[:20]:
                item_name = it.get("Name", "")
                date = it.get("Date", {})
                start = date.get("start", "") if isinstance(date, dict) else ""
                time_str = it.get("Time", it.get("시간", ""))
                place = it.get("Place", it.get("장소", ""))
                line = f"- {start} {time_str} {item_name}"
                if place:
                    line += f" @ {place}"
                lines.append(line)
            return "\n".join(lines)
        return f"'{keyword}' 관련 일정이 없습니다."

    if name == "get_reservations":
        keyword = args.get("trip_name")
        reservations = _query_reservations(keyword)
        if reservations:
            lines = [f"🏨 예약 현황 ({len(reservations)}건):"]
            for r in reservations:
                res_name = r.get("Name", "")
                status = r.get("Status", r.get("상태", ""))
                date = r.get("Date", {})
                start = date.get("start", "") if isinstance(date, dict) else ""
                cost = r.get("Cost", r.get("비용", 0))
                line = f"- {res_name} ({start})"
                if status:
                    line += f" [{status}]"
                if cost:
                    line += f" {cost:,.0f}원"
                lines.append(line)
            return "\n".join(lines)
        return "예약 정보가 없습니다."

    if name == "get_packing_list":
        keyword = args.get("trip_name")
        items = _query_packing(keyword)
        if items:
            checked = [i for i in items if i.get("Checked", i.get("체크", False))]
            unchecked = [i for i in items if not i.get("Checked", i.get("체크", False))]
            lines = [f"🎒 준비물 ({len(checked)}/{len(items)} 완료):"]
            for i in unchecked:
                lines.append(f"  ☐ {i.get('Name', '')}")
            for i in checked:
                lines.append(f"  ☑ {i.get('Name', '')}")
            return "\n".join(lines)
        return "준비물 목록이 없습니다."

    if name == "check_packing_item":
        item_name = args.get("item_name", "")
        checked = args.get("checked", True)
        items = _query_packing(item_name)
        if items:
            page_id = items[0].get("id", "")
            if page_id:
                r = update_page(page_id, {"Checked": {"checkbox": checked}})
                if r.get("success"):
                    return f"{'☑' if checked else '☐'} '{item_name}' {'체크 완료' if checked else '체크 해제'}!"
                return f"❌ 업데이트 실패: {r.get('error', '')}"
        return f"'{item_name}' 항목을 찾을 수 없습니다."

    return "알 수 없는 도구"


def handle(message, mode="chat"):
    if mode == "dday_reminder":
        trips = _query_trips("upcoming")
        today = datetime.now()
        reminders = []
        for t in trips:
            trip_name = t.get("Name", "")
            date = t.get("Date", {})
            start = date.get("start", "") if isinstance(date, dict) else ""
            if not start:
                continue
            try:
                target = datetime.strptime(start[:10], '%Y-%m-%d')
                diff = (target - today).days
                if diff in [30, 14, 7, 3, 1, 0]:
                    dday = _calc_dday(start)
                    reminders.append(f"✈️ {trip_name} {dday} ({start})")
            except Exception:
                continue
        if reminders:
            return {"response": "🔔 여행 D-day 알림:\n" + "\n".join(reminders), "domain": DOMAIN}
        return {"response": "", "domain": DOMAIN}

    if not message:
        return {"error": "메시지가 필요합니다", "domain": DOMAIN}

    trips = _query_trips()
    today = datetime.now().strftime('%Y-%m-%d')

    user_content = f"""## 여행 현황
{json.dumps(trips[:5], ensure_ascii=False, indent=1)}
오늘 날짜: {today}

## 사용자 요청
{message}"""

    text, calls = chat_with_tools(SYSTEM_PROMPT, user_content, TOOLS)
    if calls:
        resp = _exec_tool(calls[0]["name"], calls[0]["arguments"])
    else:
        resp = text

    add_to_history(DOMAIN, message, resp)
    return {"response": resp, "domain": DOMAIN}
