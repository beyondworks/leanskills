#!/usr/bin/env python3
import json
import urllib.request
import urllib.error

N8N_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhMzY2MjNkOC1jM2IyLTQ0ZTItODZkYy00MmIwNGJhNWE3YTMiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzY3OTQ2NzM1fQ.fCTlNkD3unwpyCHxXieJqBrF5kTmLf-n00IckJkqpSg"
N8N_URL = "http://localhost:5678/api/v1/workflows"

# Credential mappings
CREDENTIALS = {
    "slackApi": {"id": "67xs3j3Zo3E8M20w", "name": "Slack account"},
    "openAiApi": {"id": "muBr08vp80tYvnD0", "name": "OpenAi account"},
    "gmailOAuth2": {"id": "W7t4afVVAIjdOHwo", "name": "Gmail account"},
    "notionApi": {"id": "xw5kbbLStDNvEvBq", "name": "Notion account"},
}

# Workflow IDs to update
WORKFLOWS = {
    "8DBUrJos8nky48yi": "[리드발굴] Google Maps",
    "0A14dO0aCULf9T19": "[AI고객지원] 이메일 서포트",
    "brXuBbQgEMwJCl65": "[뉴스분석] 금융/주식",
    "qpJGn1UDX8oqzs6O": "[문서처리] Mistral OCR",
}

def get_workflow(workflow_id):
    req = urllib.request.Request(
        f"{N8N_URL}/{workflow_id}",
        headers={"X-N8N-API-KEY": N8N_API_KEY}
    )
    with urllib.request.urlopen(req) as response:
        return json.load(response)

def update_workflow(workflow_id, data):
    req = urllib.request.Request(
        f"{N8N_URL}/{workflow_id}",
        data=json.dumps(data).encode('utf-8'),
        headers={
            "X-N8N-API-KEY": N8N_API_KEY,
            "Content-Type": "application/json"
        },
        method="PUT"
    )
    with urllib.request.urlopen(req) as response:
        return json.load(response)

def add_credentials_to_nodes(nodes):
    updated = False
    for node in nodes:
        node_type = node.get("type", "")

        # Slack nodes
        if "slack" in node_type.lower():
            if "credentials" not in node:
                node["credentials"] = {}
            node["credentials"]["slackApi"] = CREDENTIALS["slackApi"]
            updated = True
            print(f"   → Slack 자격증명 연결: {node['name']}")

        # OpenAI nodes
        elif "openai" in node_type.lower() or "openAi" in node_type.lower():
            if "credentials" not in node:
                node["credentials"] = {}
            node["credentials"]["openAiApi"] = CREDENTIALS["openAiApi"]
            updated = True
            print(f"   → OpenAI 자격증명 연결: {node['name']}")

        # Gmail nodes
        elif "gmail" in node_type.lower():
            if "credentials" not in node:
                node["credentials"] = {}
            node["credentials"]["gmailOAuth2"] = CREDENTIALS["gmailOAuth2"]
            updated = True
            print(f"   → Gmail 자격증명 연결: {node['name']}")

    return nodes, updated

print("🔧 워크플로우 자격증명 업데이트 시작...")
print("")

for wf_id, wf_name in WORKFLOWS.items():
    print(f"📦 처리 중: {wf_name}")

    try:
        workflow = get_workflow(wf_id)
        nodes, updated = add_credentials_to_nodes(workflow["nodes"])

        if updated:
            update_data = {
                "name": workflow["name"],
                "nodes": nodes,
                "connections": workflow["connections"],
                "settings": workflow.get("settings", {})
            }
            update_workflow(wf_id, update_data)
            print(f"   ✅ 업데이트 완료")
        else:
            print(f"   ⏭️ 업데이트 필요 없음")
    except Exception as e:
        print(f"   ❌ 오류: {e}")

    print("")

print("✅ 자격증명 업데이트 완료!")
