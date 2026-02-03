#!/usr/bin/env python3
"""
Schedule Assistant - 완전한 AI 비서 v2
기능: 일정 조회/추가/수정/삭제, 빈 시간 확인, 미팅 노트 조회, 대화 히스토리 학습
"""

import os
import sys
import json
import urllib.request
import urllib.error
from datetime import datetime, timedelta

# 스크립트 디렉토리
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
HISTORY_FILE = os.path.join(SCRIPT_DIR, 'conversation_history.json')

# .env 파일 로드
def load_env():
    env_path = os.path.join(SCRIPT_DIR, '.env')
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value

load_env()

# 설정
NOTION_API_KEY = os.environ.get('NOTION_API_KEY', '')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
NOTION_DB_ID = "242003c7-f7be-804a-9d6e-f76d5d0347b4"
SCHEDULE_RELATION_ID = "276003c7-f7be-8012-889c-ffb91c786af1"  # Relation의 Schedule 페이지 ID

# 대화 히스토리 관리
def load_history():
    """대화 히스토리 로드"""
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {"conversations": [], "learned_patterns": {}}
    return {"conversations": [], "learned_patterns": {}}

def save_history(history):
    """대화 히스토리 저장"""
    # 최근 100개만 유지
    history["conversations"] = history["conversations"][-100:]
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def add_to_history(user_msg, assistant_msg):
    """대화 추가"""
    history = load_history()
    history["conversations"].append({
        "timestamp": datetime.now().isoformat(),
        "user": user_msg,
        "assistant": assistant_msg
    })
    save_history(history)

def get_recent_history(n=5):
    """최근 n개 대화 가져오기"""
    history = load_history()
    return history["conversations"][-n:]

def notion_request(method, endpoint, data=None):
    """Notion API 요청 헬퍼"""
    url = f"https://api.notion.com/v1/{endpoint}"

    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode('utf-8') if data else None,
        headers={
            "Authorization": f"Bearer {NOTION_API_KEY}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json"
        },
        method=method
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return {"success": True, "data": json.load(response)}
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8') if e.fp else str(e)
        return {"success": False, "error": error_body}
    except Exception as e:
        return {"success": False, "error": str(e)}

def parse_rich_text(rich_text_arr):
    """Rich text 배열에서 텍스트 추출"""
    if not rich_text_arr:
        return ""
    return "".join([t.get('plain_text', '') for t in rich_text_arr])

def parse_page(page):
    """Notion 페이지를 파싱하여 일정 정보 추출"""
    props = page.get('properties', {})

    # 제목
    name_prop = props.get('Entry name', props.get('Name', props.get('이름', {})))
    title_arr = name_prop.get('title', [])
    name = parse_rich_text(title_arr) or '(제목 없음)'

    # 날짜
    date_prop = props.get('Date', props.get('날짜', {}))
    date_obj = date_prop.get('date', {}) or {}
    date_start = date_obj.get('start', '')
    date_end = date_obj.get('end', '')

    # 완료 여부
    done_prop = props.get('Completed', props.get('Done', props.get('완료', {})))
    done = done_prop.get('checkbox', False)

    # 노트/메모
    notes_prop = props.get('Notes', props.get('노트', props.get('메모', {})))
    notes = parse_rich_text(notes_prop.get('rich_text', []))

    # 시간
    time_prop = props.get('Time (Entry)', props.get('시간', {}))
    time_entry = parse_rich_text(time_prop.get('rich_text', []))

    # 장소
    location_prop = props.get('Location (Entry)', props.get('장소', {}))
    location = parse_rich_text(location_prop.get('rich_text', []))

    # 참석자
    members_prop = props.get('Members', props.get('참석자', {}))
    members = parse_rich_text(members_prop.get('rich_text', []))

    # 카테고리
    category_prop = props.get('Category', props.get('카테고리', {}))
    category = category_prop.get('select', {})
    category_name = category.get('name', '') if category else ''

    # 상태
    status_prop = props.get('Status', props.get('상태', {}))
    status = status_prop.get('status', {})
    status_name = status.get('name', '') if status else ''

    return {
        'id': page.get('id', ''),
        'name': name,
        'date_start': date_start,
        'date_end': date_end,
        'done': done,
        'notes': notes,
        'time': time_entry,
        'location': location,
        'members': members,
        'category': category_name,
        'status': status_name,
        'url': page.get('url', '')
    }

def get_schedules_by_date_range(start_date, end_date):
    """날짜 범위로 일정 조회"""
    filter_obj = {
        "filter": {
            "and": [
                {"property": "Date", "date": {"on_or_after": start_date}},
                {"property": "Date", "date": {"on_or_before": end_date}}
            ]
        },
        "sorts": [{"property": "Date", "direction": "ascending"}],
        "page_size": 100
    }
    result = notion_request("POST", f"databases/{NOTION_DB_ID}/query", filter_obj)
    if result['success']:
        return [parse_page(p) for p in result['data'].get('results', [])]
    return []

def get_schedules_by_date(date_str):
    """특정 날짜 일정 조회"""
    filter_obj = {
        "filter": {
            "property": "Date",
            "date": {"equals": date_str}
        },
        "page_size": 100
    }
    result = notion_request("POST", f"databases/{NOTION_DB_ID}/query", filter_obj)
    if result['success']:
        return [parse_page(p) for p in result['data'].get('results', [])]
    return []

def get_incomplete_schedules():
    """미완료 일정 조회"""
    filter_obj = {
        "filter": {
            "property": "Completed",
            "checkbox": {"equals": False}
        },
        "sorts": [{"property": "Date", "direction": "ascending"}],
        "page_size": 100
    }
    result = notion_request("POST", f"databases/{NOTION_DB_ID}/query", filter_obj)
    if result['success']:
        return [parse_page(p) for p in result['data'].get('results', [])]
    return []

def search_schedules(keyword):
    """키워드로 일정 검색"""
    filter_obj = {
        "filter": {
            "property": "Entry name",
            "title": {"contains": keyword}
        },
        "sorts": [{"property": "Date", "direction": "descending"}],
        "page_size": 20
    }
    result = notion_request("POST", f"databases/{NOTION_DB_ID}/query", filter_obj)
    if result['success']:
        return [parse_page(p) for p in result['data'].get('results', [])]
    return []

def create_schedule(title, date_str, time_str=None, notes=None, location=None, members=None):
    """새 일정 생성 (Relation=Schedule 자동 설정)"""
    date_value = {"start": date_str}
    if time_str:
        date_value["start"] = f"{date_str}T{time_str}:00+09:00"

    properties = {
        "Entry name": {"title": [{"text": {"content": title}}]},
        "Date": {"date": date_value},
        "Completed": {"checkbox": False},
        "Relation": {"relation": [{"id": SCHEDULE_RELATION_ID}]}  # Schedule 자동 연결
    }

    if notes:
        properties["Notes"] = {"rich_text": [{"text": {"content": notes}}]}
    if location:
        properties["Location (Entry)"] = {"rich_text": [{"text": {"content": location}}]}
    if members:
        properties["Members"] = {"rich_text": [{"text": {"content": members}}]}

    page_data = {
        "parent": {"database_id": NOTION_DB_ID},
        "properties": properties
    }

    return notion_request("POST", "pages", page_data)

def update_schedule(page_id, updates):
    """일정 수정"""
    properties = {}

    if 'title' in updates:
        properties["Entry name"] = {"title": [{"text": {"content": updates['title']}}]}
    if 'date' in updates:
        date_value = {"start": updates['date']}
        if 'time' in updates and updates['time']:
            date_value["start"] = f"{updates['date']}T{updates['time']}:00+09:00"
        properties["Date"] = {"date": date_value}
    if 'done' in updates:
        properties["Completed"] = {"checkbox": updates['done']}
    if 'notes' in updates:
        properties["Notes"] = {"rich_text": [{"text": {"content": updates['notes']}}]}
    if 'location' in updates:
        properties["Location (Entry)"] = {"rich_text": [{"text": {"content": updates['location']}}]}

    return notion_request("PATCH", f"pages/{page_id}", {"properties": properties})

def delete_schedule(page_id):
    """일정 삭제 (archive)"""
    return notion_request("PATCH", f"pages/{page_id}", {"archived": True})

def get_all_context():
    """AI에게 제공할 전체 컨텍스트 수집"""
    today = datetime.now()

    # 날짜 계산
    yesterday = today - timedelta(days=1)
    tomorrow = today + timedelta(days=1)
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    last_week_start = week_start - timedelta(days=7)
    last_week_end = week_start - timedelta(days=1)
    next_week_start = week_end + timedelta(days=1)
    next_week_end = next_week_start + timedelta(days=6)
    two_weeks_later = today + timedelta(days=14)

    context = {
        'current_time': today.strftime('%Y-%m-%d %H:%M'),
        'current_weekday': ['월', '화', '수', '목', '금', '토', '일'][today.weekday()],
        'dates': {
            'yesterday': yesterday.strftime('%Y-%m-%d'),
            'today': today.strftime('%Y-%m-%d'),
            'tomorrow': tomorrow.strftime('%Y-%m-%d'),
            'this_week': f"{week_start.strftime('%Y-%m-%d')} ~ {week_end.strftime('%Y-%m-%d')}",
            'last_week': f"{last_week_start.strftime('%Y-%m-%d')} ~ {last_week_end.strftime('%Y-%m-%d')}",
            'next_week': f"{next_week_start.strftime('%Y-%m-%d')} ~ {next_week_end.strftime('%Y-%m-%d')}"
        },
        'schedules': {
            'yesterday': get_schedules_by_date(yesterday.strftime('%Y-%m-%d')),
            'today': get_schedules_by_date(today.strftime('%Y-%m-%d')),
            'tomorrow': get_schedules_by_date(tomorrow.strftime('%Y-%m-%d')),
            'last_week': get_schedules_by_date_range(
                last_week_start.strftime('%Y-%m-%d'),
                last_week_end.strftime('%Y-%m-%d')
            ),
            'this_week': get_schedules_by_date_range(
                today.strftime('%Y-%m-%d'),
                week_end.strftime('%Y-%m-%d')
            ),
            'next_week': get_schedules_by_date_range(
                next_week_start.strftime('%Y-%m-%d'),
                next_week_end.strftime('%Y-%m-%d')
            ),
            'next_two_weeks': get_schedules_by_date_range(
                today.strftime('%Y-%m-%d'),
                two_weeks_later.strftime('%Y-%m-%d')
            ),
            'incomplete': get_incomplete_schedules()
        }
    }

    return context

def generate_ai_response(user_message, context, mode="chat"):
    """OpenAI로 응답 생성 (GPT-4.5 사용)"""

    # 최근 대화 히스토리 가져오기
    recent_history = get_recent_history(5)
    history_text = ""
    if recent_history:
        history_text = "\n## 최근 대화 기록\n"
        for conv in recent_history:
            history_text += f"- 사용자: {conv['user']}\n- 비서: {conv['assistant'][:100]}...\n\n"

    system_prompt = """당신은 유능하고 친근한 개인 비서 '스케줄 봇'입니다. 사용자의 일정을 완벽하게 관리합니다.

## 성격
- 친근하고 자연스러운 말투
- 간결하지만 필요한 정보는 빠짐없이
- 사용자의 맥락과 의도를 잘 파악

## 핵심 역할
- 일정 조회, 추가, 수정, 삭제
- 빈 시간 확인 및 미팅 가능 여부 판단
- 미팅 노트 및 상세 정보 제공
- 일정 충돌 확인
- 과거 대화 맥락 기억

## 중요: 질문과 요청 구분
- "~가능해?", "~있어?", "~뭐야?", "~어때?", "~알려줘", "~뭐지?" → 질문 (정보 조회만)
- "~해줘", "~추가해", "~등록해", "~잡아줘", "~넣어줘" → 요청 (함수 호출)

예시:
- "내일 2시에 미팅 가능해?" → 질문 → 일정 확인 후 가능 여부만 답변
- "내일 2시에 카페에서 미팅 추가해줘" → 요청 → add_schedule(title, date, time, location)

## 함수 사용 규칙
1. **일정 추가**: 명령형("추가해", "등록해", "잡아줘")일 때만 add_schedule 사용
   - 장소 언급 시 location 파라미터 필수
   - 시간 언급 시 time 파라미터 필수
   - 참석자 언급 시 members 파라미터 사용
2. **일정 수정**: update_schedule (page_id 필요)
3. **일정 삭제**: delete_schedule (page_id 필요)
4. **일정 검색**: search_schedule (키워드로 과거 일정 찾기)

## 날짜/시간 해석
- "내일" → 내일 날짜
- "모레" → 모레 날짜
- "다음 주 월요일" → 다음 주 월요일 날짜
- "오후 2시", "2시" → 14:00
- "아침 9시" → 09:00
- "저녁 7시" → 19:00
- "점심" → 12:00

## 장소 파싱
- "카페에서", "회사에서", "OO에서" → location 추출
- "줌으로", "온라인으로" → location = "온라인/Zoom"

## 응답 스타일
- 자연스럽고 친근하게
- 이모지 적절히 사용 (📅, ✅, 📝, 📍, ⏰)
- 핵심 정보 위주로"""

    user_content = f"""## 현재 시간
{context['current_time']} ({context['current_weekday']}요일)

## 주요 날짜
- 어제: {context['dates']['yesterday']}
- 오늘: {context['dates']['today']}
- 내일: {context['dates']['tomorrow']}
- 지난 주: {context['dates']['last_week']}
- 이번 주: {context['dates']['this_week']}
- 다음 주: {context['dates']['next_week']}
{history_text}
## 어제 일정
{json.dumps(context['schedules']['yesterday'], ensure_ascii=False, indent=2)}

## 오늘 일정
{json.dumps(context['schedules']['today'], ensure_ascii=False, indent=2)}

## 내일 일정
{json.dumps(context['schedules']['tomorrow'], ensure_ascii=False, indent=2)}

## 이번 주 남은 일정
{json.dumps(context['schedules']['this_week'], ensure_ascii=False, indent=2)}

## 다음 주 일정
{json.dumps(context['schedules']['next_week'], ensure_ascii=False, indent=2)}

## 미완료 일정
{json.dumps(context['schedules']['incomplete'], ensure_ascii=False, indent=2)}

## 사용자 요청
{user_message}"""

    # GPT-5.2는 tools 파라미터 사용 (functions는 deprecated)
    tools = [
        {
            "type": "function",
            "function": {
                "name": "add_schedule",
                "description": "새 일정을 추가합니다. 명령형 요청일 때만 사용하세요.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "일정 제목"},
                        "date": {"type": "string", "description": "날짜 (YYYY-MM-DD)"},
                        "time": {"type": "string", "description": "시간 (HH:MM, 언급된 경우 필수)"},
                        "location": {"type": "string", "description": "장소 (언급된 경우 필수)"},
                        "members": {"type": "string", "description": "참석자 (언급된 경우)"},
                        "notes": {"type": "string", "description": "메모 (선택)"}
                    },
                    "required": ["title", "date"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "update_schedule",
                "description": "기존 일정을 수정합니다",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "page_id": {"type": "string", "description": "수정할 일정의 ID"},
                        "title": {"type": "string"},
                        "date": {"type": "string"},
                        "time": {"type": "string"},
                        "done": {"type": "boolean"},
                        "notes": {"type": "string"},
                        "location": {"type": "string"}
                    },
                    "required": ["page_id"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "delete_schedule",
                "description": "일정을 삭제합니다",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "page_id": {"type": "string", "description": "삭제할 일정의 ID"}
                    },
                    "required": ["page_id"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "search_schedule",
                "description": "키워드로 일정을 검색합니다",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "keyword": {"type": "string", "description": "검색 키워드"}
                    },
                    "required": ["keyword"]
                }
            }
        }
    ]

    request_data = {
        "model": "gpt-5.2",  # GPT-5.2 최신 모델 (2026년 1월 출시)
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ],
        "tools": tools,
        "tool_choice": "auto",
        "max_completion_tokens": 1000,
        "temperature": 0.4
    }

    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(request_data).encode('utf-8'),
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            result = json.load(response)
            message = result.get('choices', [{}])[0].get('message', {})

            # Tool calls 처리 (GPT-5.2 신규 포맷)
            tool_calls = message.get('tool_calls', [])
            if tool_calls:
                tool_call = tool_calls[0]  # 첫 번째 tool call만 처리
                func_name = tool_call['function']['name']
                func_args = json.loads(tool_call['function']['arguments'])

                if func_name == 'add_schedule':
                    add_result = create_schedule(
                        func_args['title'],
                        func_args['date'],
                        func_args.get('time'),
                        func_args.get('notes'),
                        func_args.get('location'),
                        func_args.get('members')
                    )
                    if add_result['success']:
                        parts = [f"✅ 일정이 추가되었습니다!"]
                        parts.append(f"📅 {func_args['date']}")
                        if func_args.get('time'):
                            parts.append(f"⏰ {func_args['time']}")
                        parts.append(f"📝 {func_args['title']}")
                        if func_args.get('location'):
                            parts.append(f"📍 {func_args['location']}")
                        if func_args.get('members'):
                            parts.append(f"👥 {func_args['members']}")
                        return "\n".join(parts)
                    else:
                        return f"❌ 일정 추가 실패: {add_result.get('error', '알 수 없는 오류')}"

                elif func_name == 'update_schedule':
                    page_id = func_args.pop('page_id')
                    update_result = update_schedule(page_id, func_args)
                    if update_result['success']:
                        return f"✅ 일정이 수정되었습니다!"
                    else:
                        return f"❌ 일정 수정 실패: {update_result.get('error', '알 수 없는 오류')}"

                elif func_name == 'delete_schedule':
                    delete_result = delete_schedule(func_args['page_id'])
                    if delete_result['success']:
                        return f"✅ 일정이 삭제되었습니다!"
                    else:
                        return f"❌ 일정 삭제 실패: {delete_result.get('error', '알 수 없는 오류')}"

                elif func_name == 'search_schedule':
                    search_results = search_schedules(func_args['keyword'])
                    if search_results:
                        return generate_search_response(user_message, search_results)
                    else:
                        return f"'{func_args['keyword']}' 관련 일정을 찾지 못했어요."

            return message.get('content', '응답 생성 실패')
    except urllib.error.HTTPError as e:
        # GPT-5.2 실패 시 GPT-5-mini로 폴백
        if "gpt-5.2" in str(e) or e.code == 404:
            request_data["model"] = "gpt-5-mini"
            req = urllib.request.Request(
                "https://api.openai.com/v1/chat/completions",
                data=json.dumps(request_data).encode('utf-8'),
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json"
                },
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=60) as response:
                result = json.load(response)
                return result.get('choices', [{}])[0].get('message', {}).get('content', '응답 생성 실패')
        return f"AI 응답 오류: {str(e)}"
    except Exception as e:
        return f"AI 응답 오류: {str(e)}"

def generate_search_response(user_message, search_results):
    """검색 결과를 바탕으로 응답 생성"""
    request_data = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": "검색된 일정 정보를 바탕으로 사용자 질문에 친근하게 답변하세요. 미팅 노트(notes)가 있으면 핵심 내용을 요약해주세요."},
            {"role": "user", "content": f"질문: {user_message}\n\n검색 결과:\n{json.dumps(search_results, ensure_ascii=False, indent=2)}"}
        ],
        "max_tokens": 500,
        "temperature": 0.3
    }

    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(request_data).encode('utf-8'),
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            result = json.load(response)
            return result.get('choices', [{}])[0].get('message', {}).get('content', '검��� 결과 처리 실패')
    except Exception as e:
        return f"검색 결과 처리 오류: {str(e)}"

def get_upcoming_reminders():
    """임박한 일정 확인 (1시간, 30분, 10분 전)"""
    now = datetime.now()
    today_str = now.strftime('%Y-%m-%d')

    # 오늘 일정 가져오기
    schedules = get_schedules_by_date(today_str)
    reminders = []

    for sch in schedules:
        if sch['done']:
            continue

        # 시간 정보 파싱
        date_start = sch.get('date_start', '')
        time_entry = sch.get('time', '')

        # ISO 형식 날짜-시간 파싱 (예: 2026-02-03T14:00:00+09:00)
        event_time = None
        if 'T' in date_start:
            try:
                # ISO 형식에서 시간 추출
                time_part = date_start.split('T')[1][:5]  # HH:MM
                hour, minute = map(int, time_part.split(':'))
                event_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            except:
                pass
        elif time_entry:
            # time 필드에서 시간 추출 (예: "14:00" 또는 "오후 2시")
            try:
                if ':' in time_entry:
                    hour, minute = map(int, time_entry.split(':')[:2])
                    event_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            except:
                pass

        if not event_time:
            continue

        # 남은 시간 계산
        diff = event_time - now
        minutes_left = diff.total_seconds() / 60

        # 리마인더 시점 확인 (±5분 범위)
        reminder_type = None
        if 55 <= minutes_left <= 65:
            reminder_type = "1시간"
        elif 25 <= minutes_left <= 35:
            reminder_type = "30분"
        elif 5 <= minutes_left <= 15:
            reminder_type = "10분"

        if reminder_type:
            reminders.append({
                'name': sch['name'],
                'time': event_time.strftime('%H:%M'),
                'reminder_type': reminder_type,
                'location': sch.get('location', ''),
                'notes': sch.get('notes', '')
            })

    return reminders

def generate_reminder_message(reminders):
    """리마인더 메시지 생성"""
    if not reminders:
        return None

    messages = []
    for r in reminders:
        msg = f"⏰ **{r['reminder_type']} 전 알림**\n"
        msg += f"📅 {r['name']} ({r['time']})"
        if r['location']:
            msg += f"\n📍 {r['location']}"
        if r['notes']:
            msg += f"\n📝 {r['notes'][:50]}"
        messages.append(msg)

    return "\n\n".join(messages)

def generate_daily_briefing(context):
    """데일리 브리핑 생성"""
    request_data = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": """당신은 친근한 개인 비서입니다. 매일 아침 브리핑을 해주세요.

형식:
🌅 **좋은 아침이에요!** [날짜]

📋 **어제 완료한 일**
- (어제 일정 중 완료된 것)

📌 **오늘 할 일**
- (오늘 일정 목록, 시간 순서대로)

💡 **오늘의 팁**
- (일정 관련 조언이나 리마인드)
"""},
            {"role": "user", "content": f"오늘: {context['dates']['today']}\n\n어제 일정:\n{json.dumps(context['schedules']['yesterday'], ensure_ascii=False)}\n\n오늘 일정:\n{json.dumps(context['schedules']['today'], ensure_ascii=False)}\n\n미완료 일정:\n{json.dumps(context['schedules']['incomplete'][:5], ensure_ascii=False)}"}
        ],
        "max_tokens": 800,
        "temperature": 0.5
    }

    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(request_data).encode('utf-8'),
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            result = json.load(response)
            return result.get('choices', [{}])[0].get('message', {}).get('content', '브리핑 생성 실패')
    except Exception as e:
        return f"브리핑 생성 오류: {str(e)}"

def generate_weekly_briefing(context):
    """위클리 브리핑 생성"""
    request_data = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": """당신은 친근한 개인 비서입니다. 매주 월요일 아침 주간 브리핑을 해주세요.

형식:
🗓️ **주간 브리핑** [날짜 범위]

📊 **지난 주 리뷰**
- 완료한 일정: X개
- 주요 완료 항목들
- 미완료된 항목 (있다면)

📅 **이번 주 계획**
- (이번 주 일정 요일별 정리)

⚠️ **주의사항**
- (중요한 마감이나 미팅)
"""},
            {"role": "user", "content": f"지난 주: {context['dates']['last_week']}\n이번 주: {context['dates']['this_week']}\n\n지난 주 일정:\n{json.dumps(context['schedules']['last_week'], ensure_ascii=False)}\n\n이번 주 일정:\n{json.dumps(context['schedules']['this_week'], ensure_ascii=False)}\n\n미완료:\n{json.dumps(context['schedules']['incomplete'][:10], ensure_ascii=False)}"}
        ],
        "max_completion_tokens": 1000,
        "temperature": 0.5
    }

    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(request_data).encode('utf-8'),
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            result = json.load(response)
            return result.get('choices', [{}])[0].get('message', {}).get('content', '주간 브리핑 생성 실패')
    except Exception as e:
        return f"주간 브리핑 생성 오류: {str(e)}"

def main():
    user_message = sys.argv[1] if len(sys.argv) > 1 else ""
    mode = sys.argv[2] if len(sys.argv) > 2 else "chat"

    if not user_message and mode == "chat":
        print(json.dumps({"error": "메시지가 필요합니다"}, ensure_ascii=False))
        sys.exit(1)

    if not NOTION_API_KEY or not OPENAI_API_KEY:
        print(json.dumps({"error": "API 키가 설정되지 않았습니다"}, ensure_ascii=False))
        sys.exit(1)

    # 전체 컨텍스트 수집
    context = get_all_context()

    # 모드별 처리
    if mode == "daily_briefing":
        ai_response = generate_daily_briefing(context)
    elif mode == "weekly_briefing":
        ai_response = generate_weekly_briefing(context)
    elif mode == "reminder":
        reminders = get_upcoming_reminders()
        ai_response = generate_reminder_message(reminders)
        if not ai_response:
            # 리마인더 없으면 빈 응답
            print(json.dumps({"response": None, "has_reminder": False}, ensure_ascii=False))
            sys.exit(0)
    else:
        ai_response = generate_ai_response(user_message, context, mode)
        # 대화 히스토리에 저장
        add_to_history(user_message, ai_response)

    # 결과 출력
    result = {"response": ai_response}
    print(json.dumps(result, ensure_ascii=False))

if __name__ == "__main__":
    main()
