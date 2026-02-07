"""Workspace-wide Notion assistant domain.

Provides dynamic search/schema-aware CRUD over arbitrary Notion databases.
Acts as the universal AI agent for all Notion-backed queries.
"""

import json
from datetime import datetime, timedelta
from core.config import get_domain_config
from core.openai_client import (
    chat_completion,
    chat_with_tools_multi,
    REQUEST_USER_CHOICE_TOOL,
    LEARN_RULE_TOOL,
)
from core.memory import get_rules_as_prompt
from core.notion_client import (
    search_workspace,
    get_database_schema,
    retrieve_page,
    query_database,
    create_page,
    update_page,
    archive_page,
    parse_page_properties,
    build_properties_from_values,
    get_title_property_name,
)

DOMAIN = "workspace"

PLAIN_TEXT_RULE = "\n\n## 응답 규칙\n- 반드시 플레인 텍스트로 응답. 마크다운 문법은 사용하지 마세요.\n- 한국어로 간결하게 답변하세요."


def _build_db_catalog():
    """Build a DB catalog string from config.json for the system prompt."""
    lines = []
    all_configs = {}
    for domain_name in ["schedule", "content", "finance", "travel", "tools", "business"]:
        cfg = get_domain_config(domain_name)
        if cfg:
            all_configs[domain_name] = cfg

    catalog = {
        "schedule": {
            "tasks": "일정/할일 (Entry name, Date, Completed, Notes, Location)",
        },
        "finance": {
            "manager": "수입/지출 내역",
            "accounts": "계좌 목록",
        },
        "tools": {
            "subscribe": "구독 서비스 (Entry name, Monthly Fee, Status, Plan, Payment Date)",
            "work_tool": "업무 도구",
            "api_archive": "API 키/계정 정보 (Entry name, API Key)",
        },
        "content": {
            "AI": "AI 콘텐츠", "Design": "디자인 콘텐츠",
            "insights": "인사이트", "news": "뉴스",
        },
        "travel": {
            "trips": "여행 계획",
            "itinerary": "여행 일정",
        },
        "business": {
            "main": "비즈니스 메인",
            "memo_archive": "메모 아카이브",
        },
    }

    for domain_name, db_desc_map in catalog.items():
        cfg = all_configs.get(domain_name, {})
        dbs = cfg.get("databases", {})
        for db_key, description in db_desc_map.items():
            db_id = dbs.get(db_key, "")
            if db_id:
                lines.append(f"- {description}: {db_id}")

    return "\n".join(lines)


SYSTEM_PROMPT = """당신은 Notion을 속속들이 알고 있는 만능 AI 비서입니다.

## 핵심 역할
- 사용자의 모든 질문에 Notion 데이터를 기반으로 정확히 답변
- 일정, 구독, 도구, 콘텐츠, 재무, 여행 등 모든 영역 커버
- 정보가 바로 없으면 관련 DB를 찾아서 조회

## 중요: 시간대 (Timezone)
- 모든 시간은 한국 시간(KST, UTC+9) 기준입니다.
- 사용자가 "오전 10시"라고 하면 KST 10:00입니다.
- 절대로 UTC 변환하지 마세요. 사용자가 말한 시간을 그대로 사용하세요.
- 일정에 시간 포함 시: "YYYY-MM-DDT10:00:00+09:00" 형식 사용
- 예: "오전 10시" → "2026-02-08T10:00:00+09:00", "오후 3시" → "2026-02-08T15:00:00+09:00"

## 알고 있는 주요 데이터베이스
{db_catalog}

## 재무(지출/수입) 기록 방법
재무 Timeline DB (database_id는 DB 카탈로그 참조) 속성:
- Entry (title): 거래 내역명 (예: "시계 구매", "커피")
- Amount (number): 금액 (양수)
- Date (date): 거래일 (예: "2026-02-07")
- Type (select): "지출" 또는 "수입"
- Memo (rich_text): 메모
지출/수입 기록 시 create_record 사용. values 예시: {{"Entry": "시계 구매", "Amount": 10000000, "Date": "2026-02-07", "Type": "지출"}}

## 일정 조회/수정 방법
일정 DB (database_id는 DB 카탈로그 참조) 속성:
- Entry name (title): 일정 제목
- Date (date): 날짜/시간
- Completed (checkbox): 완료 여부
- Notes (rich_text): 메모
- Location (Entry) (rich_text): 장소

일정 검색 시:
1. 먼저 query_with_filter로 날짜 범위 필터링해서 후보를 가져옴
2. 제목으로 찾을 때 contains 필터 사용 (부분 일치: "아카데미" → "아카데미 이동" 매칭)
3. 결과에서 page_id를 사용해 update_record로 수정

일정 수정 예시:
1. query_with_filter로 해당 일정 검색 → page_id 확보
2. update_record(page_id=..., values={{"Date": "2026-02-08T10:00:00+09:00"}})

## 자주 쓰는 필터 패턴
- 특정 날짜 일정: {{"property": "Date", "date": {{"equals": "2026-02-04"}}}}
- 날짜 범위: {{"and": [{{"property": "Date", "date": {{"on_or_after": "2026-02-01"}}}}, {{"property": "Date", "date": {{"on_or_before": "2026-02-07"}}}}]}}
- 미완료 항목: {{"property": "Completed", "checkbox": {{"equals": false}}}}
- 활성 구독: {{"property": "Status", "status": {{"equals": "Subscribe"}}}}
- 제목 검색: {{"property": "Entry name", "title": {{"contains": "키워드"}}}}

## 사고 방식
1. 질문을 분석하여 어떤 DB가 필요한지 판단
2. 필요하면 query_with_filter로 정확한 필터를 적용해 조회
3. 결과가 없으면 search_workspace로 범위를 넓혀 검색
4. 찾은 데이터를 기반으로 명확하게 답변

## 작업 원칙
- "모르겠습니다" 대신 반드시 관련 DB를 조회해서 답변 시도
- 쓰기 작업(create/update/archive)은 반드시 실행하고, 실패 시 에러를 정확히 보고
- 결과에 page_id/database_id 포함하지 않아도 됨 (사용자에게 불필요)
- 오류 시 이유와 대안을 간단히 제시
- create_record 호출 후 "기록 완료"라고 응답하기 전에 반드시 성공 여부를 확인""" + PLAIN_TEXT_RULE

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_workspace",
            "description": "워크스페이스 전체에서 페이지/데이터베이스 검색",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "검색어"},
                    "object_type": {
                        "type": "string",
                        "description": "page|database|page_or_database",
                        "enum": ["page", "database", "page_or_database"],
                    },
                    "limit": {"type": "integer", "description": "최대 결과 수"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "inspect_database",
            "description": "데이터베이스 스키마(필드 구조) 조회",
            "parameters": {
                "type": "object",
                "properties": {
                    "database_id": {"type": "string", "description": "Notion database ID"}
                },
                "required": ["database_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_records",
            "description": "데이터베이스 레코드 조회 (키워드 검색)",
            "parameters": {
                "type": "object",
                "properties": {
                    "database_id": {"type": "string", "description": "Notion database ID"},
                    "keyword": {"type": "string", "description": "타이틀 검색 키워드"},
                    "limit": {"type": "integer", "description": "최대 결과 수"},
                },
                "required": ["database_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_with_filter",
            "description": "Notion 필터로 데이터베이스 조회. 날짜, 상태, 체크박스 등 고급 필터 지원",
            "parameters": {
                "type": "object",
                "properties": {
                    "database_id": {"type": "string", "description": "Notion database ID"},
                    "filter": {
                        "type": "object",
                        "description": "Notion API 필터 객체. 예: {\"property\": \"Date\", \"date\": {\"equals\": \"2026-02-04\"}}",
                    },
                    "sorts": {
                        "type": "array",
                        "description": "정렬 배열. 예: [{\"property\": \"Date\", \"direction\": \"ascending\"}]",
                    },
                    "limit": {"type": "integer", "description": "최대 결과 수 (기본 20)"},
                },
                "required": ["database_id", "filter"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_record",
            "description": "데이터베이스에 새 레코드 생성",
            "parameters": {
                "type": "object",
                "properties": {
                    "database_id": {"type": "string"},
                    "values": {
                        "type": "object",
                        "description": "키=값 형태의 필드 값 (예: {\"title\":\"간식\",\"amount\":20000})",
                    },
                },
                "required": ["database_id", "values"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_record",
            "description": "기존 레코드의 필드 수정",
            "parameters": {
                "type": "object",
                "properties": {
                    "page_id": {"type": "string"},
                    "values": {"type": "object"},
                },
                "required": ["page_id", "values"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "archive_record",
            "description": "레코드 보관(아카이브)",
            "parameters": {
                "type": "object",
                "properties": {
                    "page_id": {"type": "string"},
                },
                "required": ["page_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "summarize_records",
            "description": "조회한 레코드를 요약 브리핑",
            "parameters": {
                "type": "object",
                "properties": {
                    "database_id": {"type": "string"},
                    "keyword": {"type": "string"},
                    "limit": {"type": "integer"},
                },
                "required": ["database_id"],
            },
        },
    },
]


def _parse_values(values):
    if isinstance(values, dict):
        return values
    if isinstance(values, str):
        try:
            parsed = json.loads(values)
            if isinstance(parsed, dict):
                return parsed
        except (json.JSONDecodeError, TypeError):
            return {}
    return {}


def _format_search_results(results, limit):
    lines = [f"검색 결과: {len(results[:limit])}건"]
    for item in results[:limit]:
        obj = item.get("object", "")
        title = ""
        if obj == "database":
            title = "".join(t.get("plain_text", "") for t in item.get("title", []))
            dbid = item.get("id", "")
            lines.append(f"- [DB] {title or '(제목 없음)'} (database_id: {dbid})")
        else:
            props = item.get("properties", {})
            for _, pv in props.items():
                if pv.get("type") == "title":
                    title = "".join(t.get("plain_text", "") for t in pv.get("title", []))
                    break
            pid = item.get("id", "")
            lines.append(f"- [PAGE] {title or '(제목 없음)'} (page_id: {pid})")
    return "\n".join(lines)


def _exec_tool(name, args):
    if name == "search_workspace":
        query = args.get("query", "")
        object_type = args.get("object_type", "page_or_database")
        limit = int(args.get("limit", 10) or 10)
        sr = search_workspace(query, object_type=object_type, page_size=min(limit, 100))
        if not sr.get("success"):
            return f"검색 실패: {sr.get('error', 'unknown error')}"
        return _format_search_results(sr.get("results", []), limit)

    if name == "inspect_database":
        database_id = args.get("database_id", "")
        schema_res = get_database_schema(database_id)
        if not schema_res.get("success"):
            return f"스키마 조회 실패: {schema_res.get('error', 'unknown error')}"

        schema = schema_res.get("schema", {})
        title_prop = get_title_property_name(schema)
        lines = [
            f"데이터베이스: {schema_res.get('title', '(제목 없음)')}",
            f"database_id: {database_id}",
            f"title_property: {title_prop or '(없음)'}",
            "속성:",
        ]
        for prop_name, prop_def in schema.items():
            lines.append(f"- {prop_name}: {prop_def.get('type', 'unknown')}")
        return "\n".join(lines)

    if name == "query_records":
        database_id = args.get("database_id", "")
        keyword = args.get("keyword", "")
        limit = int(args.get("limit", 10) or 10)

        schema_res = get_database_schema(database_id)
        if not schema_res.get("success"):
            return f"DB 스키마 조회 실패: {schema_res.get('error', 'unknown error')}"

        schema = schema_res.get("schema", {})
        filter_obj = None
        if keyword:
            title_prop = get_title_property_name(schema)
            if title_prop:
                filter_obj = {"property": title_prop, "title": {"contains": keyword}}

        qr = query_database(
            database_id,
            filter_obj=filter_obj,
            page_size=min(limit, 100),
            max_results=limit,
        )
        if not qr.get("success"):
            return f"레코드 조회 실패: {qr.get('error', 'unknown error')}"

        parsed = [parse_page_properties(p) for p in qr.get("results", [])]
        if not parsed:
            return "조회된 레코드가 없습니다."

        lines = [f"레코드 {len(parsed)}건"]
        for row in parsed:
            parts = []
            for key, val in row.items():
                if key == "id":
                    continue
                if val is None or val == "" or val == []:
                    continue
                if isinstance(val, list):
                    val = ", ".join(str(v) for v in val)
                parts.append(f"{key}: {val}")
            lines.append("- " + " | ".join(parts))
        return "\n".join(lines)

    if name == "query_with_filter":
        database_id = args.get("database_id", "")
        filter_obj = args.get("filter")
        sorts = args.get("sorts")
        limit = int(args.get("limit", 20) or 20)

        if isinstance(filter_obj, str):
            try:
                filter_obj = json.loads(filter_obj)
            except (json.JSONDecodeError, TypeError):
                return "필터 JSON 파싱 실패. 올바른 Notion 필터 객체를 전달하세요."

        if isinstance(sorts, str):
            try:
                sorts = json.loads(sorts)
            except (json.JSONDecodeError, TypeError):
                sorts = None

        qr = query_database(
            database_id,
            filter_obj=filter_obj,
            sorts=sorts,
            page_size=min(limit, 100),
            max_results=limit,
        )
        if not qr.get("success"):
            return f"필터 조회 실패: {qr.get('error', 'unknown error')}"

        parsed = [parse_page_properties(p) for p in qr.get("results", [])]
        if not parsed:
            return "조건에 맞는 레코드가 없습니다."

        lines = [f"조회 결과: {len(parsed)}건"]
        for row in parsed:
            parts = []
            for key, val in row.items():
                if key == "id":
                    continue
                if val is None or val == "" or val == []:
                    continue
                if isinstance(val, list):
                    val = ", ".join(str(v) for v in val)
                parts.append(f"{key}: {val}")
            lines.append("- " + " | ".join(parts))
        return "\n".join(lines)

    if name == "create_record":
        database_id = args.get("database_id", "")
        values = _parse_values(args.get("values"))

        schema_res = get_database_schema(database_id)
        if not schema_res.get("success"):
            return f"DB 스키마 조회 실패: {schema_res.get('error', 'unknown error')}"

        schema = schema_res.get("schema", {})
        properties = build_properties_from_values(schema, values)

        title_prop = get_title_property_name(schema)
        if title_prop and title_prop not in properties:
            fallback_title = values.get("title") or values.get("name") or values.get("entry") or "새 항목"
            properties[title_prop] = {"title": [{"text": {"content": str(fallback_title)}}]}

        if not properties:
            return "생성할 필드 값이 없습니다. values를 확인하세요."

        cr = create_page(database_id, properties)
        if not cr.get("success"):
            return f"레코드 생성 실패: {cr.get('error', 'unknown error')}"

        created = cr.get("data", {})
        return f"생성 완료 (page_id: {created.get('id', '')})"

    if name == "update_record":
        page_id = args.get("page_id", "")
        values = _parse_values(args.get("values"))

        page_res = retrieve_page(page_id)
        if not page_res.get("success"):
            return f"페이지 조회 실패: {page_res.get('error', 'unknown error')}"

        page = page_res.get("page", {})
        parent = page.get("parent", {})
        database_id = parent.get("database_id", "")
        if not database_id:
            return "해당 페이지는 데이터베이스 기반 레코드가 아닙니다."

        schema_res = get_database_schema(database_id)
        if not schema_res.get("success"):
            return f"DB 스키마 조회 실패: {schema_res.get('error', 'unknown error')}"

        schema = schema_res.get("schema", {})
        properties = build_properties_from_values(schema, values)
        if not properties:
            return "수정할 필드 값이 없습니다. values를 확인하세요."

        ur = update_page(page_id, properties)
        if not ur.get("success"):
            return f"레코드 수정 실패: {ur.get('error', 'unknown error')}"
        return f"수정 완료 (page_id: {page_id})"

    if name == "archive_record":
        page_id = args.get("page_id", "")
        ar = archive_page(page_id)
        if not ar.get("success"):
            return f"보관 실패: {ar.get('error', 'unknown error')}"
        return f"보관 완료 (page_id: {page_id})"

    if name == "summarize_records":
        database_id = args.get("database_id", "")
        keyword = args.get("keyword", "")
        limit = int(args.get("limit", 20) or 20)

        schema_res = get_database_schema(database_id)
        if not schema_res.get("success"):
            return f"DB 스키마 조회 실패: {schema_res.get('error', 'unknown error')}"

        schema = schema_res.get("schema", {})
        filter_obj = None
        if keyword:
            title_prop = get_title_property_name(schema)
            if title_prop:
                filter_obj = {"property": title_prop, "title": {"contains": keyword}}

        qr = query_database(database_id, filter_obj=filter_obj, page_size=min(limit, 100), max_results=limit)
        if not qr.get("success"):
            return f"레코드 조회 실패: {qr.get('error', 'unknown error')}"

        parsed = [parse_page_properties(p) for p in qr.get("results", [])]
        if not parsed:
            return "요약할 데이터가 없습니다."

        content = json.dumps(parsed, ensure_ascii=False)
        summary = chat_completion(
            [
                {"role": "system", "content": "당신은 Notion 데이터 요약 비서입니다. 핵심만 한국어로 짧게 요약하세요."},
                {"role": "user", "content": content},
            ],
            max_tokens=800,
            temperature=0.2,
        )
        return summary or "요약 결과가 없습니다."

    return "알 수 없는 도구"


def handle(message, mode="chat", session=None, image_urls=None):
    if not message:
        return {"error": "메시지가 필요합니다", "domain": DOMAIN}

    messages = []
    if session and session.get("messages"):
        messages = list(session["messages"][-16:])

    # DB 카탈로그와 현재 날짜를 시스템 프롬프트에 주입
    now = datetime.now()
    db_catalog = _build_db_catalog()
    date_context = (
        f"\n\n## 현재 시각 정보\n"
        f"- 현재: {now.strftime('%Y-%m-%d %H:%M')} ({['월','화','수','목','금','토','일'][now.weekday()]}요일)\n"
        f"- 이번 주: {(now - timedelta(days=now.weekday())).strftime('%Y-%m-%d')} ~ "
        f"{(now + timedelta(days=6 - now.weekday())).strftime('%Y-%m-%d')}"
    )
    system_prompt = SYSTEM_PROMPT.format(db_catalog=db_catalog) + date_context

    messages.append({"role": "user", "content": message})

    learned_rules = get_rules_as_prompt(DOMAIN)
    result = chat_with_tools_multi(
        system_prompt + learned_rules,
        messages,
        TOOLS + [REQUEST_USER_CHOICE_TOOL, LEARN_RULE_TOOL],
        _exec_tool,
        domain=DOMAIN,
        image_urls=image_urls,
    )

    output = {
        "response": result.get("response", ""),
        "domain": DOMAIN,
        "learning_events": result.get("learning_events", []),
    }
    if result.get("interactive"):
        output["interactive"] = result["interactive"]
    return output
