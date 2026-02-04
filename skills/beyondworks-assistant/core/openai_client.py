"""OpenAI API client (stdlib only)"""
import json
import urllib.request
import urllib.error
from .config import get_openai_key


def chat_completion(messages, model="gpt-4o-mini", max_tokens=1000, temperature=0.4):
    body = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature
    }
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(body).encode('utf-8'),
        headers={
            "Authorization": f"Bearer {get_openai_key()}",
            "Content-Type": "application/json"
        },
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.load(resp)
            return result['choices'][0]['message'].get('content', '')
    except Exception as e:
        return f"AI 응답 오류: {e}"


def chat_with_tools(system_prompt, user_content, tools, model="gpt-4o-mini", max_tokens=1000):
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ],
        "tools": tools,
        "tool_choice": "auto",
        "max_tokens": max_tokens,
        "temperature": 0.4
    }
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(body).encode('utf-8'),
        headers={
            "Authorization": f"Bearer {get_openai_key()}",
            "Content-Type": "application/json"
        },
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.load(resp)
            msg = result['choices'][0]['message']
            tool_calls = msg.get('tool_calls', [])
            if tool_calls:
                calls = []
                for tc in tool_calls:
                    calls.append({
                        "name": tc['function']['name'],
                        "arguments": json.loads(tc['function']['arguments'])
                    })
                return msg.get('content', ''), calls
            return msg.get('content', ''), []
    except Exception as e:
        return f"AI 응답 오류: {e}", []


def classify_domain(message, domain_keywords):
    domains_desc = "\n".join(
        f"- {name}: {', '.join(kw)}" for name, kw in domain_keywords.items()
    )
    prompt = f"""사용자 메시지를 분석하여 가장 적절한 도메인 하나를 선택하세요.

도메인 목록:
{domains_desc}

규칙:
- 반드시 도메인 이름만 출력 (schedule, content, finance, travel, tools, business)
- 판단이 어려우면 schedule 선택

사용자 메시지: {message}

도메인:"""
    result = chat_completion(
        [{"role": "user", "content": prompt}],
        model="gpt-4o-mini",
        max_tokens=20,
        temperature=0
    )
    result = result.strip().lower()
    valid = {"schedule", "content", "finance", "travel", "tools", "business"}
    for d in valid:
        if d in result:
            return d
    return "schedule"
