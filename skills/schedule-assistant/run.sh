#!/bin/bash
# Schedule Assistant - Notion 일정 조회 + OpenAI 응답 생성

# 설정
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CONFIG_FILE="$SCRIPT_DIR/config.json"

# 환경 변수 로드 (있으면)
if [ -f "$SCRIPT_DIR/.env" ]; then
    source "$SCRIPT_DIR/.env"
fi

# API 키 (환경 변수에서 가져오거나 직접 설정)
NOTION_API_KEY="${NOTION_API_KEY:-}"
OPENAI_API_KEY="${OPENAI_API_KEY:-}"

# Notion 설정
NOTION_DB_ID="242003c7-f7be-804a-9d6e-f76d5d0347b4"

# 사용자 메시지
USER_MESSAGE="$1"

if [ -z "$USER_MESSAGE" ]; then
    echo '{"error": "메시지가 필요합니다"}'
    exit 1
fi

# 오늘 날짜
TODAY=$(date +%Y-%m-%d)

# 1. Notion에서 오늘 일정 조회
get_notion_schedules() {
    local filter_json=$(cat <<EOF
{
    "filter": {
        "property": "Date",
        "date": {
            "equals": "$TODAY"
        }
    },
    "page_size": 100
}
EOF
)

    curl -s -X POST "https://api.notion.com/v1/databases/$NOTION_DB_ID/query" \
        -H "Authorization: Bearer $NOTION_API_KEY" \
        -H "Notion-Version: 2022-06-28" \
        -H "Content-Type: application/json" \
        -d "$filter_json"
}

# 2. 미완료 일정 조회
get_incomplete_schedules() {
    local filter_json=$(cat <<EOF
{
    "filter": {
        "property": "Done",
        "checkbox": {
            "equals": false
        }
    },
    "page_size": 100
}
EOF
)

    curl -s -X POST "https://api.notion.com/v1/databases/$NOTION_DB_ID/query" \
        -H "Authorization: Bearer $NOTION_API_KEY" \
        -H "Notion-Version: 2022-06-28" \
        -H "Content-Type: application/json" \
        -d "$filter_json"
}

# 3. Notion 결과 파싱
parse_notion_results() {
    local json="$1"
    echo "$json" | python3 -c "
import sys, json

try:
    data = json.load(sys.stdin)
    results = data.get('results', [])
    schedules = []

    for page in results:
        props = page.get('properties', {})

        # 제목 추출
        name_prop = props.get('Name', props.get('이름', props.get('제목', {})))
        title_arr = name_prop.get('title', [])
        name = title_arr[0].get('plain_text', '') if title_arr else '(제목 없음)'

        # 날짜 추출
        date_prop = props.get('Date', props.get('날짜', {}))
        date_obj = date_prop.get('date', {})
        date = date_obj.get('start', '') if date_obj else ''

        # 완료 여부
        done_prop = props.get('Done', props.get('완료', {}))
        done = done_prop.get('checkbox', False)

        schedules.append({
            'name': name,
            'date': date,
            'done': done
        })

    print(json.dumps(schedules, ensure_ascii=False))
except Exception as e:
    print(json.dumps([]))
"
}

# 4. OpenAI로 응답 생성
generate_response() {
    local schedules="$1"
    local incomplete="$2"

    local system_prompt="당신은 친절한 일정 비서입니다. 사용자의 일정 관련 질문에 한국어로 간결하게 답변하세요."

    local user_content="오늘 날짜: $TODAY

오늘 일정:
$schedules

미완료 일정:
$incomplete

사용자 질문: $USER_MESSAGE"

    local request_json=$(python3 -c "
import json
data = {
    'model': 'gpt-4o-mini',
    'messages': [
        {'role': 'system', 'content': '''$system_prompt'''},
        {'role': 'user', 'content': '''$user_content'''}
    ],
    'max_tokens': 500,
    'temperature': 0.7
}
print(json.dumps(data, ensure_ascii=False))
")

    curl -s -X POST "https://api.openai.com/v1/chat/completions" \
        -H "Authorization: Bearer $OPENAI_API_KEY" \
        -H "Content-Type: application/json" \
        -d "$request_json"
}

# 5. OpenAI 응답에서 텍스트 추출
extract_response() {
    local json="$1"
    echo "$json" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    content = data.get('choices', [{}])[0].get('message', {}).get('content', '')
    print(content)
except:
    print('응답 생성에 실패했습니다.')
"
}

# 메인 실행
main() {
    # API 키 확인
    if [ -z "$NOTION_API_KEY" ] || [ -z "$OPENAI_API_KEY" ]; then
        echo "API 키가 설정되지 않았습니다. .env 파일을 확인하세요."
        exit 1
    fi

    # Notion 조회
    today_raw=$(get_notion_schedules)
    incomplete_raw=$(get_incomplete_schedules)

    # 파싱
    today_schedules=$(parse_notion_results "$today_raw")
    incomplete_schedules=$(parse_notion_results "$incomplete_raw")

    # OpenAI 응답 생성
    ai_response_raw=$(generate_response "$today_schedules" "$incomplete_schedules")
    ai_response=$(extract_response "$ai_response_raw")

    # 결과 출력 (JSON)
    python3 -c "
import json
result = {
    'response': '''$ai_response''',
    'today': $today_schedules,
    'incomplete': $incomplete_schedules
}
print(json.dumps(result, ensure_ascii=False))
"
}

main
