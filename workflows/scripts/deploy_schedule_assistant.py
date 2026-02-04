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
    "notionApi": {"id": "xw5kbbLStDNvEvBq", "name": "Notion account"},
}

def load_workflow(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def add_credentials_to_workflow(workflow):
    """Add credentials to nodes based on node type"""
    for node in workflow.get("nodes", []):
        node_type = node.get("type", "").lower()

        # Slack nodes
        if "slack" in node_type:
            if "credentials" not in node:
                node["credentials"] = {}
            node["credentials"]["slackApi"] = CREDENTIALS["slackApi"]
            print(f"   → Slack 자격증명 연결: {node['name']}")

        # OpenAI nodes
        if "openai" in node_type or "lmchatopenai" in node_type:
            if "credentials" not in node:
                node["credentials"] = {}
            node["credentials"]["openAiApi"] = CREDENTIALS["openAiApi"]
            print(f"   → OpenAI 자격증명 연결: {node['name']}")

        # Notion nodes
        if "notion" in node_type:
            if "credentials" not in node:
                node["credentials"] = {}
            node["credentials"]["notionApi"] = CREDENTIALS["notionApi"]
            print(f"   → Notion 자격증명 연결: {node['name']}")

    return workflow

def deploy_workflow(workflow):
    """Deploy workflow to n8n"""
    data = json.dumps(workflow).encode('utf-8')

    req = urllib.request.Request(
        N8N_URL,
        data=data,
        headers={
            "X-N8N-API-KEY": N8N_API_KEY,
            "Content-Type": "application/json"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req) as response:
            result = json.load(response)
            return result
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        print(f"HTTP Error {e.code}: {error_body}")
        return None

def main():
    print("🚀 Notion-Slack 스케줄 비서 워크플로우 배포 시작...")
    print("")

    # Load workflow
    workflow_file = "/Users/yoogeon/n8n/docker/workflows/notion-slack-schedule-assistant.json"
    print(f"📄 워크플로우 파일 로드: {workflow_file}")
    workflow = load_workflow(workflow_file)
    print(f"   워크플로우 이름: {workflow['name']}")
    print(f"   노드 수: {len(workflow.get('nodes', []))}")
    print("")

    # Add credentials
    print("🔑 자격증명 연결 중...")
    workflow = add_credentials_to_workflow(workflow)
    print("")

    # Deploy
    print("📤 n8n에 배포 중...")
    result = deploy_workflow(workflow)

    if result:
        workflow_id = result.get('id', 'unknown')
        workflow_name = result.get('name', 'unknown')
        print(f"   ✅ 배포 성공!")
        print(f"   ID: {workflow_id}")
        print(f"   이름: {workflow_name}")
        print(f"   URL: http://localhost:5678/workflow/{workflow_id}")
        print("")
        print("⚠️ 다음 설정이 필요합니다:")
        print("   1. Slack App 설정:")
        print("      - Event Subscriptions 활성화")
        print("      - Request URL: http://[your-domain]:5678/webhook/schedule-slack-trigger")
        print("      - Subscribe to bot events: message.channels")
        print("   2. Slack Interactive Components:")
        print("      - Request URL: http://[your-domain]:5678/webhook/schedule-button-callback")
        print("   3. #schedule 채널 생성 및 봇 초대")
        print("   4. 워크플로우 활성화 (n8n UI에서)")
    else:
        print("   ❌ 배포 실패")

    print("")
    print("✅ 완료!")

if __name__ == "__main__":
    main()
