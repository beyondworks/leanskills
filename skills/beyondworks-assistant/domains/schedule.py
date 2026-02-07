"""Schedule domain handler — 일정/업무 관리"""
import json
from datetime import datetime, timedelta
from core.config import get_domain_config
from core.notion_client import query_database, create_page, update_page, archive_page, parse_page_properties
from core.openai_client import (
    chat_completion,
    chat_with_tools_multi,
    REQUEST_USER_CHOICE_TOOL,
    LEARN_RULE_TOOL,
)
from core.memory import get_rules_as_prompt

DOMAIN = "schedule"
CFG = None

PLAIN_TEXT_RULE = "\n\n## 응답 규칙\n- 반드시 플레인 텍스트로 응답. **bold**, [link](url), # heading, `code` 등 마크다운 절대 금지.\n- 이모지 사용 가능."


def _cfg():
    global CFG
    if CFG is None:
        CFG = get_domain_config(DOMAIN)
    return CFG


def _db(key):
    return _cfg().get("databases", {}).get(key, "")


SYSTEM_PROMPT = """당신은 유능하고 친근한 개인 비서입니다. 사용자의 일정을 관리합니다.

## 핵심 역할
- 일정 조회/추가/수정/삭제, 빈 시간 확인, 일정 충돌 확인

## 질문 vs 요청 구분
- "~가능해?", "~있어?", "~알려줘" → 정보 조회만
- "~해줘", "~추가해", "~잡아줘" → 함수 호출

## 중요: 시간대 (Timezone)
- 모든 시간은 한국 시간(KST, UTC+9) 기준입니다.
- 컨텍스트에 표시된 current_time은 KST입니다.
- 사용자가 "오전 10시"라고 하면 KST 10:00 = HH:MM 형식으로 "10:00"입니다.
- 절대로 UTC 변환하지 마세요. 사용자가 말한 시간을 그대로 HH:MM으로 전달하세요.
- 예: "오전 10시" → time: "10:00", "오후 3시" → time: "15:00"

## 날짜/시간 해석
- "내일" → 내일, "모레" → 모레, "다음 주 월요일" → 계산
- "오후 2시" → 14:00, "아침 9시" → 09:00

## 누락 정보 처리
- 일정 추가 시 날짜나 시간이 누락되면, request_user_choice 도구를 사용하여 선택지를 제시하세요.

## 응답 스타일
- 한국어, 친근하게""" + PLAIN_TEXT_RULE

TOOLS = [
    {"type": "function", "function": {
        "name": "add_schedule",
        "description": "새 일정 추가 (명령형일 때만)",
        "parameters": {"type": "object", "properties": {
            "title": {"type": "string"}, "date": {"type": "string", "description": "YYYY-MM-DD"},
            "time": {"type": "string", "description": "HH:MM"}, "location": {"type": "string"},
            "members": {"type": "string"}, "notes": {"type": "string"}
        }, "required": ["title", "date"]}
    }},
    {"type": "function", "function": {
        "name": "update_schedule", "description": "일정 수정",
        "parameters": {"type": "object", "properties": {
            "page_id": {"type": "string"}, "title": {"type": "string"},
            "date": {"type": "string"}, "time": {"type": "string"},
            "done": {"type": "boolean"}, "notes": {"type": "string"}, "location": {"type": "string"}
        }, "required": ["page_id"]}
    }},
    {"type": "function", "function": {
        "name": "delete_schedule", "description": "일정 삭제",
        "parameters": {"type": "object", "properties": {
            "page_id": {"type": "string"}
        }, "required": ["page_id"]}
    }},
    {"type": "function", "function": {
        "name": "search_schedule", "description": "키워드로 일정 검색",
        "parameters": {"type": "object", "properties": {
            "keyword": {"type": "string"}
        }, "required": ["keyword"]}
    }}
]


def _query_by_date(date_str):
    return query_database(_db("tasks"),
        filter_obj={"property": "Date", "date": {"equals": date_str}},
        sorts=[{"property": "Date", "direction": "ascending"}])


def _query_by_range(start, end):
    return query_database(_db("tasks"),
        filter_obj={"and": [
            {"property": "Date", "date": {"on_or_after": start}},
            {"property": "Date", "date": {"on_or_before": end}}
        ]}, sorts=[{"property": "Date", "direction": "ascending"}])


def _query_incomplete():
    return query_database(_db("tasks"),
        filter_obj={"property": "Completed", "checkbox": {"equals": False}},
        sorts=[{"property": "Date", "direction": "ascending"}])


def _search(keyword):
    return query_database(_db("tasks"),
        filter_obj={"property": "Entry name", "title": {"contains": keyword}},
        sorts=[{"property": "Date", "direction": "descending"}])


def _results_to_list(qr):
    if isinstance(qr, dict):
        return [parse_page_properties(p) for p in qr.get("results", [])]
    return qr


def _get_context():
    now = datetime.now()
    yesterday = now - timedelta(days=1)
    tomorrow = now + timedelta(days=1)
    week_end = now + timedelta(days=(6 - now.weekday()))
    next_week_start = week_end + timedelta(days=1)
    next_week_end = next_week_start + timedelta(days=6)

    return {
        "current_time": now.strftime('%Y-%m-%d %H:%M'),
        "weekday": ['월','화','수','목','금','토','일'][now.weekday()],
        "yesterday": _results_to_list(_query_by_date(yesterday.strftime('%Y-%m-%d'))),
        "today": _results_to_list(_query_by_date(now.strftime('%Y-%m-%d'))),
        "tomorrow": _results_to_list(_query_by_date(tomorrow.strftime('%Y-%m-%d'))),
        "this_week": _results_to_list(_query_by_range(now.strftime('%Y-%m-%d'), week_end.strftime('%Y-%m-%d'))),
        "next_week": _results_to_list(_query_by_range(next_week_start.strftime('%Y-%m-%d'), next_week_end.strftime('%Y-%m-%d'))),
        "incomplete": _results_to_list(_query_incomplete()),
        "dates": {
            "yesterday": yesterday.strftime('%Y-%m-%d'),
            "today": now.strftime('%Y-%m-%d'),
            "tomorrow": tomorrow.strftime('%Y-%m-%d'),
        }
    }


def _exec_tool(name, args):
    if name == "add_schedule":
        date_str = args["date"]
        if args.get("time"):
            date_val = {"start": f"{date_str}T{args['time']}:00+09:00"}
        elif "T" in date_str and "+09:00" not in date_str and "+" not in date_str.split("T")[1]:
            date_val = {"start": f"{date_str}+09:00"}
        else:
            date_val = {"start": date_str}
        props = {
            "Entry name": {"title": [{"text": {"content": args["title"]}}]},
            "Date": {"date": date_val},
            "Completed": {"checkbox": False},
            "Relation": {"relation": [{"id": _cfg().get("schedule_relation_id", "")}]}
        }
        if args.get("notes"):
            props["Notes"] = {"rich_text": [{"text": {"content": args["notes"]}}]}
        if args.get("location"):
            props["Location (Entry)"] = {"rich_text": [{"text": {"content": args["location"]}}]}
        if args.get("members"):
            props["Members"] = {"rich_text": [{"text": {"content": args["members"]}}]}
        r = create_page(_db("tasks"), props)
        if r["success"]:
            parts = [f"일정 추가 완료! {args['date']}"]
            if args.get("time"):
                parts.append(f"{args['time']}")
            parts.append(f"{args['title']}")
            if args.get("location"):
                parts.append(f"장소: {args['location']}")
            return "\n".join(parts)
        return f"추가 실패: {r.get('error','')}"

    if name == "update_schedule":
        pid = args.pop("page_id")
        props = {}
        if "title" in args:
            props["Entry name"] = {"title": [{"text": {"content": args["title"]}}]}
        if "date" in args:
            date_str = args["date"]
            if args.get("time"):
                dv = {"start": f"{date_str}T{args['time']}:00+09:00"}
            elif "T" in date_str and "+09:00" not in date_str and "+" not in date_str.split("T")[1]:
                # AI가 ISO 형식으로 보냈지만 timezone 없으면 KST 추가
                dv = {"start": f"{date_str}+09:00" if not date_str.endswith("+09:00") else date_str}
            else:
                dv = {"start": date_str}
            props["Date"] = {"date": dv}
        if "done" in args:
            props["Completed"] = {"checkbox": args["done"]}
        if "notes" in args:
            props["Notes"] = {"rich_text": [{"text": {"content": args["notes"]}}]}
        if "location" in args:
            props["Location (Entry)"] = {"rich_text": [{"text": {"content": args["location"]}}]}
        r = update_page(pid, props)
        return "수정 완료!" if r["success"] else f"수정 실패: {r.get('error','')}"

    if name == "delete_schedule":
        r = archive_page(args["page_id"])
        return "삭제 완료!" if r["success"] else f"삭제 실패: {r.get('error','')}"

    if name == "search_schedule":
        results = _results_to_list(_search(args["keyword"]))
        if results:
            lines = [f"'{args['keyword']}' 검색 결과:"]
            for s in results[:10]:
                lines.append(f"- {s.get('Entry name','')} ({s.get('Date','')})")
            return "\n".join(lines)
        return f"'{args['keyword']}' 관련 일정을 찾지 못했어요."

    return "알 수 없는 도구"


def _briefing(ctx, mode):
    if mode == "daily_briefing":
        prompt = "매일 아침 브리핑: 어제 완료, 오늘 할 일, 미완료 항목 정리. 이모지 사용. 한국어."
        content = f"오늘: {ctx['dates']['today']}\n어제 일정: {json.dumps(ctx['yesterday'], ensure_ascii=False)}\n오늘 일정: {json.dumps(ctx['today'], ensure_ascii=False)}\n미완료: {json.dumps(ctx['incomplete'][:5], ensure_ascii=False)}"
    elif mode == "weekly_briefing":
        prompt = "주간 브리핑: 이번 주 일정 요약, 미완료 항목, 주의사항. 이모지 사용. 한국어."
        content = f"이번 주: {json.dumps(ctx['this_week'], ensure_ascii=False)}\n다음 주: {json.dumps(ctx['next_week'], ensure_ascii=False)}\n미완료: {json.dumps(ctx['incomplete'][:10], ensure_ascii=False)}"
    else:
        return None
    return chat_completion([{"role": "system", "content": prompt}, {"role": "user", "content": content}], max_tokens=800, temperature=0.5)


def _reminder(ctx):
    now = datetime.now()
    reminders = []
    for s in ctx["today"]:
        if s.get("Completed"):
            continue
        date_val = s.get("Date", "")
        if isinstance(date_val, dict):
            date_val = date_val.get("start", "")
        if "T" in str(date_val):
            try:
                tp = str(date_val).split("T")[1][:5]
                h, m = map(int, tp.split(":"))
                event_time = now.replace(hour=h, minute=m, second=0, microsecond=0)
                diff = (event_time - now).total_seconds() / 60
                rtype = None
                if 55 <= diff <= 65:
                    rtype = "1시간"
                elif 25 <= diff <= 35:
                    rtype = "30분"
                elif 5 <= diff <= 15:
                    rtype = "10분"
                if rtype:
                    reminders.append(f"{rtype} 전: {s.get('Entry name','')} ({tp})")
            except Exception:
                pass
    return "\n".join(reminders) if reminders else None


def handle(message, mode="chat", session=None, image_urls=None):
    ctx = _get_context()

    if mode in ("daily_briefing", "weekly_briefing"):
        resp = _briefing(ctx, mode)
        return {"response": resp, "domain": DOMAIN}

    if mode == "reminder":
        resp = _reminder(ctx)
        return {"response": resp, "has_reminder": resp is not None, "domain": DOMAIN}

    if not message:
        return {"error": "메시지가 필요합니다", "domain": DOMAIN}

    context = f"""## 현재 {ctx['current_time']} KST ({ctx['weekday']}요일) — 모든 시간은 한국 시간(KST) 기준
## 날짜: 어제={ctx['dates']['yesterday']} 오늘={ctx['dates']['today']} 내일={ctx['dates']['tomorrow']}
## 오늘 일정
{json.dumps(ctx['today'][:10], ensure_ascii=False, indent=1)}
## 내일 일정
{json.dumps(ctx['tomorrow'][:10], ensure_ascii=False, indent=1)}
## 이번 주 남은 일정
{json.dumps(ctx['this_week'][:15], ensure_ascii=False, indent=1)}
## 미완료
{json.dumps(ctx['incomplete'][:10], ensure_ascii=False, indent=1)}"""

    # Build messages from session history
    messages = []
    if session and session.get("messages"):
        messages = list(session["messages"][-16:])
    messages.append({"role": "user", "content": f"{context}\n\n## 사용자 요청\n{message}"})

    learned_rules = get_rules_as_prompt(DOMAIN)
    result = chat_with_tools_multi(
        SYSTEM_PROMPT + learned_rules, messages,
        TOOLS + [REQUEST_USER_CHOICE_TOOL, LEARN_RULE_TOOL], _exec_tool,
        domain=DOMAIN, image_urls=image_urls
    )

    output = {
        "response": result["response"],
        "domain": DOMAIN,
        "learning_events": result.get("learning_events", []),
    }
    if result.get("interactive"):
        output["interactive"] = result["interactive"]
    return output
