#!/bin/bash

N8N_API_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhMzY2MjNkOC1jM2IyLTQ0ZTItODZkYy00MmIwNGJhNWE3YTMiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzY3OTQ2NzM1fQ.fCTlNkD3unwpyCHxXieJqBrF5kTmLf-n00IckJkqpSg"
N8N_URL="http://localhost:5678/api/v1/workflows"

deploy_workflow() {
    local file=$1
    local name=$(basename "$file" .json)

    echo "📦 Deploying: $name"

    response=$(curl -s -X POST "$N8N_URL" \
        -H "X-N8N-API-KEY: $N8N_API_KEY" \
        -H "Content-Type: application/json" \
        -d @"$file")

    if echo "$response" | grep -q '"id"'; then
        id=$(echo "$response" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
        wf_name=$(echo "$response" | python3 -c "import sys,json; print(json.load(sys.stdin)['name'])")
        echo "   ✅ Success: $wf_name (ID: $id)"
    else
        echo "   ❌ Failed: $response"
    fi
}

echo "🚀 Starting workflow deployment..."
echo ""

# Deploy each workflow
for file in /Users/yoogeon/n8n/docker/workflows/*-kr.json; do
    deploy_workflow "$file"
done

echo ""
echo "✅ Deployment complete!"
