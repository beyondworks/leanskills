#!/usr/bin/env python3
import json
import urllib.request
import urllib.error

N8N_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhMzY2MjNkOC1jM2IyLTQ0ZTItODZkYy00MmIwNGJhNWE3YTMiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzY3OTQ2NzM1fQ.fCTlNkD3unwpyCHxXieJqBrF5kTmLf-n00IckJkqpSg"
N8N_URL = "http://localhost:5678/api/v1/workflows"
FOLDER_ID = "6ZjUBC8WxQ7SB4xH"  # 260203_클로드코드

# New workflow IDs
WORKFLOWS = [
    "8DBUrJos8nky48yi",  # Google Maps
    "0A14dO0aCULf9T19",  # AI Email Support
    "brXuBbQgEMwJCl65",  # Finance News
    "qpJGn1UDX8oqzs6O",  # Mistral OCR
    "t18S6XFAdUajyM6b",  # First Google Maps (duplicate)
]

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

def delete_workflow(workflow_id):
    req = urllib.request.Request(
        f"{N8N_URL}/{workflow_id}",
        headers={"X-N8N-API-KEY": N8N_API_KEY},
        method="DELETE"
    )
    try:
        with urllib.request.urlopen(req) as response:
            return True
    except:
        return False

print("📁 워크플로우 폴더 이동 시작...")
print(f"   대상 폴더: 260203_클로드코드 ({FOLDER_ID})")
print("")

# Delete duplicate first
print("🗑️ 중복 워크플로우 삭제: t18S6XFAdUajyM6b")
if delete_workflow("t18S6XFAdUajyM6b"):
    print("   ✅ 삭제 완료")
else:
    print("   ⚠️ 삭제 실패 또는 이미 없음")
print("")

# Note: n8n API doesn't support moving workflows to folders directly
# Folder assignment is typically done through the UI or database

print("📝 참고: 폴더 이동은 n8n 웹 UI에서 수행해주세요.")
print("")
print("🔗 워크플로우 목록:")
for wf_id in WORKFLOWS[:-1]:  # Exclude deleted duplicate
    try:
        wf = get_workflow(wf_id)
        print(f"   - {wf['name']}")
        print(f"     http://localhost:5678/workflow/{wf_id}")
    except Exception as e:
        pass

print("")
print("✅ 완료!")
