"""Content & Knowledge domain handler — 콘텐츠/지식 관리"""
import json
from datetime import datetime, timedelta
from core.config import get_domain_config
from core.notion_client import query_database, create_page, parse_page_properties
from core.openai_client import chat_with_tools, chat_completion
from core.history import add_to_history, get_recent_history

DOMAIN = "content"

def _cfg():
    return get_domain_config(DOMAIN)

def _db(key):
    return _cfg().get("databases", {}).get(key, "")

SYSTEM_PROMPT = """당신은 콘텐츠/지식 관리 비서입니다. 8개 DB(AI, Design, Branding, Build, Marketing, 인사이트, News & Tips, Scrap)를 관리합니다.

## 역할
- 카테고리별/키워드별 콘텐츠 검색
- 인사이트 요약, 콘텐츠 추천
- URL 스크랩 추가

## 응답 스타일
- 한국어, 간결하게, 핵심 위주"""

TOOLS = [
    {"type": "function", "function": {
        "name": "search_content",
        "description": "카테고리/키워드로 콘텐츠 검색",
        "parameters": {"type": "object", "properties": {
            "category": {"type": "string", "description": "AI, Design, Branding, Build, Marketing, news, scrap 중 택1"},
            "keyword": {"type": "string"}
        }}
    }},
    {"type": "function", "function": {
        "name": "add_scrap",
        "description": "URL을 스크랩 DB에 저장",
        "parameters": {"type": "object", "properties": {
            "url": {"type": "string"}, "title": {"type": "string"}, "category": {"type": "string"}
        }, "required": ["url"]}
    }},
    {"type": "function", "function": {
        "name": "get_recent_entries",
        "description": "특정 카테고리의 최근 콘텐츠 조회",
        "parameters": {"type": "object", "properties": {
            "category": {"type": "string", "description": "AI, Design, Branding, Build, Marketing"},
            "count": {"type": "integer", "description": "조회 개수 (기본 5)"}
        }, "required": ["category"]}
    }}
]

CATEGORY_DB_MAP = {
    "AI": "AI", "Design": "Design", "Branding": "Branding",
    "Build": "Build", "Marketing": "Marketing",
    "news": "news", "scrap": "scrap", "insights": "insights"
}

def _query_category(cat, keyword=None, limit=10):
    db_key = CATEGORY_DB_MAP.get(cat, cat)
    db_id = _db(db_key)
    if not db_id:
        return []
    filt = None
    if keyword:
        # Try title search
        title_prop = "Title" if cat == "scrap" else "Entry name"
        filt = {"property": title_prop, "title": {"contains": keyword}}
    r = query_database(db_id, filter_obj=filt,
                       sorts=[{"property": "Date", "direction": "descending"}],
                       page_size=limit)
    if isinstance(r, dict):
        return [parse_page_properties(p) for p in r.get("results", [])]
    return r

def _exec_tool(name, args):
    if name == "search_content":
        cat = args.get("category", "")
        kw = args.get("keyword", "")
        if cat:
            results = _query_category(cat, kw)
        else:
            results = []
            for c in ["AI", "Design", "Build", "Marketing", "news"]:
                results.extend(_query_category(c, kw, 3))
        if results:
            lines = [f"🔍 검색 결과 ({len(results)}건):"]
            for r in results[:15]:
                title = r.get("Entry name", r.get("Title", ""))
                url = r.get("URL", "")
                lines.append(f"- {title}" + (f" ({url})" if url else ""))
            return "\n".join(lines)
        return "검색 결과가 없습니다."

    if name == "add_scrap":
        props = {
            "Title": {"title": [{"text": {"content": args.get("title", args["url"])}}]},
            "URL": {"url": args["url"]},
            "Date": {"date": {"start": datetime.now().strftime('%Y-%m-%d')}},
            "Status": {"select": {"name": "New"}}
        }
        if args.get("category"):
            props["Categories"] = {"multi_select": [{"name": args["category"]}]}
        r = create_page(_db("scrap"), props)
        return f"✅ 스크랩 저장 완료!" if r["success"] else f"❌ 실패: {r.get('error','')}"

    if name == "get_recent_entries":
        cat = args.get("category", "AI")
        count = args.get("count", 5)
        results = _query_category(cat, limit=count)
        if results:
            lines = [f"📚 {cat} 최근 {len(results)}건:"]
            for r in results:
                title = r.get("Entry name", "")
                tags = r.get("Tags", [])
                tag_str = " ".join(f"#{t}" for t in tags[:3]) if tags else ""
                lines.append(f"- {title} {tag_str}")
            return "\n".join(lines)
        return f"{cat} 카테고리에 콘텐츠가 없습니다."

    return "알 수 없는 도구"

def handle(message, mode="chat"):
    if mode == "weekly_digest":
        lines = ["📊 *주간 콘텐츠 다이제스트*\n"]
        for cat in ["AI", "Design", "Build", "Marketing"]:
            results = _query_category(cat, limit=3)
            if results:
                lines.append(f"*{cat}*")
                for r in results:
                    lines.append(f"  - {r.get('Entry name','')}")
        resp = "\n".join(lines)
        return {"response": resp, "domain": DOMAIN}

    if not message:
        return {"error": "메시지가 필요합니다", "domain": DOMAIN}

    recent = []
    for cat in ["AI", "Design", "Build"]:
        recent.extend(_query_category(cat, limit=3))

    user_content = f"""## 최근 콘텐츠 (샘플)
{json.dumps(recent[:10], ensure_ascii=False, indent=1)}

## 사용자 요청
{message}"""

    text, calls = chat_with_tools(SYSTEM_PROMPT, user_content, TOOLS)
    if calls:
        resp = _exec_tool(calls[0]["name"], calls[0]["arguments"])
    else:
        resp = text

    add_to_history(DOMAIN, message, resp)
    return {"response": resp, "domain": DOMAIN}
