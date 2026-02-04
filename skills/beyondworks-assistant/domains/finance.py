"""Finance domain handler — 재무 관리"""
import json
from datetime import datetime, timedelta
from core.config import get_domain_config
from core.notion_client import query_database, create_page, parse_page_properties
from core.openai_client import chat_with_tools, chat_completion
from core.history import add_to_history, get_recent_history

DOMAIN = "finance"

def _cfg():
    return get_domain_config(DOMAIN)

def _db(key):
    return _cfg().get("databases", {}).get(key, "")

SYSTEM_PROMPT = """당신은 재무 관리 비서입니다. 계좌, 지출, 예산을 관리합니다.

## 역할
- 잔액/지출/수입 조회
- 거래 기록 추가
- 카테고리별 분석, 월간 리포트
- 예산 대비 현황

## 응답 스타일
- 한국어, 금액은 원 단위로, 간결하게"""

TOOLS = [
    {"type": "function", "function": {
        "name": "get_accounts",
        "description": "계좌 목록 및 잔액 조회",
        "parameters": {"type": "object", "properties": {}}
    }},
    {"type": "function", "function": {
        "name": "add_transaction",
        "description": "지출/수입 거래 기록 추가",
        "parameters": {"type": "object", "properties": {
            "entry": {"type": "string", "description": "거래 내용"},
            "amount": {"type": "number", "description": "금액"},
            "category": {"type": "string", "description": "카테고리 (식비, 교통, 쇼핑 등)"},
            "type": {"type": "string", "description": "수입 또는 지출"},
            "memo": {"type": "string"}
        }, "required": ["entry", "amount"]}
    }},
    {"type": "function", "function": {
        "name": "get_transactions",
        "description": "거래 내역 조회 (기간/키워드)",
        "parameters": {"type": "object", "properties": {
            "keyword": {"type": "string"},
            "start_date": {"type": "string", "description": "YYYY-MM-DD"},
            "end_date": {"type": "string", "description": "YYYY-MM-DD"}
        }}
    }},
    {"type": "function", "function": {
        "name": "get_categories",
        "description": "카테고리별 예산/지출 현황",
        "parameters": {"type": "object", "properties": {}}
    }}
]

def _query_accounts():
    r = query_database(_db("accounts"))
    if isinstance(r, dict):
        return [parse_page_properties(p) for p in r.get("results", [])]
    return r

def _query_transactions(keyword=None, start=None, end=None, limit=20):
    filters = []
    if keyword:
        filters.append({"property": "Entry", "title": {"contains": keyword}})
    if start:
        filters.append({"property": "\x08Date", "date": {"on_or_after": start}})
    if end:
        filters.append({"property": "\x08Date", "date": {"on_or_before": end}})
    filt = {"and": filters} if len(filters) > 1 else (filters[0] if filters else None)
    r = query_database(_db("timeline"), filter_obj=filt,
                       sorts=[{"property": "\x08Date", "direction": "descending"}],
                       page_size=limit)
    if isinstance(r, dict):
        return [parse_page_properties(p) for p in r.get("results", [])]
    return r

def _query_categories():
    r = query_database(_db("categories"))
    if isinstance(r, dict):
        return [parse_page_properties(p) for p in r.get("results", [])]
    return r

def _exec_tool(name, args):
    if name == "get_accounts":
        accs = _query_accounts()
        if accs:
            lines = ["💰 계좌 현황:"]
            for a in accs:
                bank = a.get("Bank", a.get("이름", ""))
                bal = a.get("잔액", a.get("Current Balance", 0))
                lines.append(f"- {bank}: {bal:,.0f}원" if bal else f"- {bank}")
            return "\n".join(lines)
        return "계좌 정보가 없습니다."

    if name == "add_transaction":
        props = {
            "Entry": {"title": [{"text": {"content": args["entry"]}}]},
            "Amount": {"number": args["amount"]},
            "\x08Date": {"date": {"start": datetime.now().strftime('%Y-%m-%d')}}
        }
        if args.get("category"):
            props["Category"] = {"select": {"name": args["category"]}}
        if args.get("type"):
            props["Type"] = {"select": {"name": args["type"]}}
        if args.get("memo"):
            props["Memo"] = {"rich_text": [{"text": {"content": args["memo"]}}]}
        r = create_page(_db("timeline"), props)
        return f"✅ 거래 기록 완료! {args['entry']} {args['amount']:,.0f}원" if r["success"] else f"❌ 실패: {r.get('error','')}"

    if name == "get_transactions":
        txns = _query_transactions(args.get("keyword"), args.get("start_date"), args.get("end_date"))
        if txns:
            lines = [f"📋 거래 내역 ({len(txns)}건):"]
            total = 0
            for t in txns[:15]:
                entry = t.get("Entry", "")
                amt = t.get("Amount", 0) or 0
                cat = t.get("Category", "")
                total += amt
                lines.append(f"- {entry}: {amt:,.0f}원 [{cat}]")
            lines.append(f"\n합계: {total:,.0f}원")
            return "\n".join(lines)
        return "거래 내역이 없습니다."

    if name == "get_categories":
        cats = _query_categories()
        if cats:
            lines = ["📊 카테고리별 현황:"]
            for c in cats:
                name_ = c.get("항목", "")
                budget = c.get("한 달 예산", 0) or 0
                spent = c.get("이번 달 지출", 0) or 0
                lines.append(f"- {name_}: 지출 {spent:,.0f}원 / 예산 {budget:,.0f}원")
            return "\n".join(lines)
        return "카테고리 정보가 없습니다."

    return "알 수 없는 도구"


def handle(message, mode="chat"):
    if mode == "monthly_report":
        accs = _query_accounts()
        cats = _query_categories()
        now = datetime.now()
        first = now.replace(day=1).strftime('%Y-%m-%d')
        txns = _query_transactions(start=first, end=now.strftime('%Y-%m-%d'))
        prompt = "월간 재무 리포트 생성. 계좌 잔액, 카테고리별 지출, 총 지출/수입 요약. 이모지 사용. 한국어."
        content = f"계좌: {json.dumps(accs[:5], ensure_ascii=False)}\n카테고리: {json.dumps(cats[:10], ensure_ascii=False)}\n이번 달 거래: {json.dumps(txns[:20], ensure_ascii=False)}"
        resp = chat_completion([{"role": "system", "content": prompt}, {"role": "user", "content": content}], max_tokens=800)
        return {"response": resp, "domain": DOMAIN}

    if mode == "weekly_expense":
        now = datetime.now()
        week_start = (now - timedelta(days=now.weekday())).strftime('%Y-%m-%d')
        txns = _query_transactions(start=week_start, end=now.strftime('%Y-%m-%d'))
        total = sum((t.get("Amount", 0) or 0) for t in txns)
        resp = f"📊 이번 주 지출: {total:,.0f}원 ({len(txns)}건)"
        return {"response": resp, "domain": DOMAIN}

    if not message:
        return {"error": "메시지가 필요합니다", "domain": DOMAIN}

    accs = _query_accounts()
    now = datetime.now()
    recent_txns = _query_transactions(start=(now - timedelta(days=7)).strftime('%Y-%m-%d'), limit=10)

    user_content = f"""## 계좌 현황
{json.dumps(accs[:5], ensure_ascii=False, indent=1)}
## 최근 7일 거래
{json.dumps(recent_txns[:10], ensure_ascii=False, indent=1)}

## 사용자 요청
{message}"""

    text, calls = chat_with_tools(SYSTEM_PROMPT, user_content, TOOLS)
    if calls:
        resp = _exec_tool(calls[0]["name"], calls[0]["arguments"])
    else:
        resp = text

    add_to_history(DOMAIN, message, resp)
    return {"response": resp, "domain": DOMAIN}
