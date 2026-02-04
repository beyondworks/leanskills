"""Business Hub domain handler — 비즈니스 허브"""
import json
from datetime import datetime
from core.config import get_domain_config, load_config
from core.notion_client import query_database, create_page, parse_page_properties
from core.openai_client import chat_with_tools, chat_completion
from core.history import add_to_history, get_recent_history

DOMAIN = "business"

def _cfg():
    return get_domain_config(DOMAIN)

def _db(key):
    return _cfg().get("databases", {}).get(key, "")

SYSTEM_PROMPT = """당신은 비즈니스 관리 비서입니다. 메모, 역량 평가, 템플릿, 크로스 도메인 검색을 관리합니다.

## 역할
- 메모 작성/검색
- 핵심 역량 평가 조회
- 워크스페이스 전체 검색
- 템플릿 조회

## 응답 스타일
- 한국어, 간결하게, 핵심 위주"""

TOOLS = [
    {"type": "function", "function": {
        "name": "search_workspace",
        "description": "워크스페이스 전체 검색 (크로스 도메인)",
        "parameters": {"type": "object", "properties": {
            "keyword": {"type": "string", "description": "검색 키워드"}
        }, "required": ["keyword"]}
    }},
    {"type": "function", "function": {
        "name": "get_memos",
        "description": "메모 아카이브 검색/조회",
        "parameters": {"type": "object", "properties": {
            "keyword": {"type": "string"},
            "count": {"type": "integer", "description": "조회 개수 (기본 10)"}
        }}
    }},
    {"type": "function", "function": {
        "name": "add_memo",
        "description": "메모 작성",
        "parameters": {"type": "object", "properties": {
            "title": {"type": "string", "description": "메모 제목"},
            "content": {"type": "string", "description": "메모 내용"},
            "tags": {"type": "array", "items": {"type": "string"}, "description": "태그 목록"}
        }, "required": ["title"]}
    }},
    {"type": "function", "function": {
        "name": "get_competency",
        "description": "핵심 역량 평가 조회",
        "parameters": {"type": "object", "properties": {}}
    }},
    {"type": "function", "function": {
        "name": "get_templates",
        "description": "템플릿 목록 조회",
        "parameters": {"type": "object", "properties": {
            "keyword": {"type": "string"}
        }}
    }}
]

def _query_memos(keyword=None, limit=10):
    db_id = _db("memo_archive")
    if not db_id:
        return []
    filt = None
    if keyword:
        filt = {"property": "Name", "title": {"contains": keyword}}
    r = query_database(db_id, filter_obj=filt,
                       sorts=[{"property": "Created", "direction": "descending"}],
                       page_size=limit)
    if isinstance(r, dict) and r.get("success"):
        return [parse_page_properties(p) for p in r.get("results", [])]
    return []

def _query_competency():
    db_id = _db("competency")
    if not db_id:
        return []
    r = query_database(db_id, page_size=20)
    if isinstance(r, dict) and r.get("success"):
        return [parse_page_properties(p) for p in r.get("results", [])]
    return []

def _query_templates(keyword=None):
    db_id = _db("templates")
    if not db_id:
        return []
    filt = None
    if keyword:
        filt = {"property": "Name", "title": {"contains": keyword}}
    r = query_database(db_id, filter_obj=filt, page_size=20)
    if isinstance(r, dict) and r.get("success"):
        return [parse_page_properties(p) for p in r.get("results", [])]
    return []

def _search_across_domains(keyword, limit_per_db=3):
    """Search across all domains for a keyword."""
    config = load_config()
    all_results = []
    for domain_name, domain_cfg in config.get("domains", {}).items():
        dbs = domain_cfg.get("databases", {})
        for db_key, db_id in dbs.items():
            if not db_id:
                continue
            filt = {"property": "Name", "title": {"contains": keyword}}
            r = query_database(db_id, filter_obj=filt, page_size=limit_per_db)
            if isinstance(r, dict) and r.get("success"):
                for p in r.get("results", []):
                    parsed = parse_page_properties(p)
                    parsed["_domain"] = domain_name
                    parsed["_db"] = db_key
                    all_results.append(parsed)
    return all_results

def _exec_tool(name, args):
    if name == "search_workspace":
        keyword = args.get("keyword", "")
        results = _search_across_domains(keyword)
        if results:
            lines = [f"🔍 '{keyword}' 전체 검색 ({len(results)}건):"]
            grouped = {}
            for r in results:
                domain = r.get("_domain", "unknown")
                if domain not in grouped:
                    grouped[domain] = []
                grouped[domain].append(r)
            domain_labels = {
                "schedule": "📅 일정", "content": "📚 콘텐츠",
                "finance": "💰 재무", "travel": "✈️ 여행",
                "tools": "🔧 도구", "business": "💼 비즈니스"
            }
            for domain, items in grouped.items():
                label = domain_labels.get(domain, domain)
                lines.append(f"\n{label}:")
                for item in items[:5]:
                    title = item.get("Name", item.get("Entry name", item.get("Entry", "")))
                    url = item.get("url", "")
                    db_name = item.get("_db", "")
                    line = f"  - {title}"
                    if db_name:
                        line += f" [{db_name}]"
                    lines.append(line)
            return "\n".join(lines)
        return f"'{keyword}'에 대한 검색 결과가 없습니다."

    if name == "get_memos":
        keyword = args.get("keyword")
        count = args.get("count", 10)
        memos = _query_memos(keyword, count)
        if memos:
            lines = [f"📝 메모 ({len(memos)}건):"]
            for m in memos:
                title = m.get("Name", "")
                created = m.get("Created", m.get("created_time", ""))
                tags = m.get("Tags", [])
                tag_str = " ".join(f"#{t}" for t in tags[:3]) if isinstance(tags, list) and tags else ""
                line = f"- {title}"
                if created:
                    line += f" ({str(created)[:10]})"
                if tag_str:
                    line += f" {tag_str}"
                lines.append(line)
            return "\n".join(lines)
        return "메모가 없습니다."

    if name == "add_memo":
        props = {
            "Name": {"title": [{"text": {"content": args["title"]}}]},
            "Created": {"date": {"start": datetime.now().strftime('%Y-%m-%d')}}
        }
        if args.get("content"):
            props["Content"] = {"rich_text": [{"text": {"content": args["content"][:2000]}}]}
        if args.get("tags"):
            props["Tags"] = {"multi_select": [{"name": t} for t in args["tags"][:5]]}
        r = create_page(_db("memo_archive"), props)
        return f"✅ 메모 저장 완료! '{args['title']}'" if r.get("success") else f"❌ 실패: {r.get('error', '')}"

    if name == "get_competency":
        items = _query_competency()
        if items:
            lines = ["📊 핵심 역량 평가:"]
            for c in items:
                comp_name = c.get("Name", c.get("이름", ""))
                score = c.get("Score", c.get("점수", c.get("Level", "")))
                status = c.get("Status", c.get("상태", ""))
                line = f"- {comp_name}"
                if score:
                    line += f": {score}"
                if status:
                    line += f" [{status}]"
                lines.append(line)
            return "\n".join(lines)
        return "역량 평가 정보가 없습니다."

    if name == "get_templates":
        keyword = args.get("keyword")
        templates = _query_templates(keyword)
        if templates:
            lines = [f"📋 템플릿 ({len(templates)}건):"]
            for t in templates:
                tpl_name = t.get("Name", "")
                category = t.get("Category", t.get("카테고리", ""))
                url = t.get("url", "")
                line = f"- {tpl_name}"
                if category:
                    line += f" [{category}]"
                lines.append(line)
            return "\n".join(lines)
        return "템플릿이 없습니다."

    return "알 수 없는 도구"


def handle(message, mode="chat"):
    if not message:
        return {"error": "메시지가 필요합니다", "domain": DOMAIN}

    recent_memos = _query_memos(limit=5)

    user_content = f"""## 최근 메모
{json.dumps(recent_memos[:5], ensure_ascii=False, indent=1)}

## 사용자 요청
{message}"""

    text, calls = chat_with_tools(SYSTEM_PROMPT, user_content, TOOLS)
    if calls:
        resp = _exec_tool(calls[0]["name"], calls[0]["arguments"])
    else:
        resp = text

    add_to_history(DOMAIN, message, resp)
    return {"response": resp, "domain": DOMAIN}
